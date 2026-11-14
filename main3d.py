"""ODYSSEY | The Fractured Sea, 3D version (Panda3D).

Uses the same planner (core/chronos.py), navigator (core/navigator.py) and
voyages (core/scenario.py, copied from main.py) as the 2D game. Only the
drawing is different.

Run:  .venv/bin/python main3d.py
Keys: SPACE start/pause, R reset, 1 SEA, 2 DEMO, 3 VOYAGE (arrow keys,
      N new map), Esc quit

(Uses Panda3D directly: Ursina's built-in shaders don't compile on macOS.)
"""

import math
import random

from panda3d.core import (
    loadPrcFileData, AmbientLight, DirectionalLight, Vec3, Vec4, NodePath,
    GeomVertexFormat, GeomVertexData, GeomVertexWriter, GeomTriangles, Geom,
    GeomNode, TextNode, Material, KeyboardButton,
)

loadPrcFileData("", "win-size 1280 760\nwindow-title ODYSSEY | The Fractured Sea"
                    "\naudio-library-name null\nframebuffer-multisample 1"
                    "\nmultisamples 4")

from direct.showbase.ShowBase import ShowBase  # noqa: E402
from direct.gui.OnscreenText import OnscreenText  # noqa: E402

from core import scenario, voyage  # noqa: E402
from core.chronos import ChronosPlanner  # noqa: E402
from core.navigator import Navigator  # noqa: E402


def rgb(r, g, b):
    return Vec4(r / 255, g / 255, b / 255, 1)


# Same palette as main.py, plus 3D materials
NAVY = rgb(8, 22, 38)
GOLD = rgb(218, 175, 104)
WHITE = rgb(230, 224, 210)
MUTED = rgb(120, 145, 160)
DANGER = rgb(175, 65, 70)
SAFE = rgb(55, 125, 115)
SEA = rgb(28, 82, 124)
ROCK = rgb(122, 110, 96)
GRASS = rgb(96, 116, 66)
WOOD = rgb(112, 72, 40)
DARK_WOOD = rgb(70, 45, 25)
KRAKEN_RED = rgb(150, 38, 58)

STEP_SECONDS_3D = 0.5    # real seconds per grid cell (2x the 2D game)

ARROW_MOVES = {"arrow_up": (0, -1), "arrow_down": (0, 1),
               "arrow_left": (-1, 0), "arrow_right": (1, 0)}
ARROW_BUTTONS = {"arrow_up": KeyboardButton.up(),
                 "arrow_down": KeyboardButton.down(),
                 "arrow_left": KeyboardButton.left(),
                 "arrow_right": KeyboardButton.right()}


# =============================================================================
# 1. Grid / pixels -> 3D world
#    One grid cell (25 px) = 1 unit. x = right, y = "up the screen", z = up.
# =============================================================================

def px_to_world(px, py, z=0.0):
    x = px / scenario.CELL_SIZE - scenario.GRID_WIDTH / 2
    y = scenario.GRID_HEIGHT / 2 - py / scenario.CELL_SIZE
    return Vec3(x, y, z)


def cell_to_world(gx, gy, z=0.0):
    return px_to_world(*scenario.grid_to_pixel(gx, gy), z=z)


# =============================================================================
# 2. Smooth playback of a planner path (same rule as main.py's
#    get_ship_position, plus which way the ship faces)
# =============================================================================

DIRECTION_ANGLE = {(1, 0): 0.0, (-1, 0): 180.0, (0, 1): 90.0, (0, -1): -90.0}


def position_at(path, t):
    """Ship position in (fractional) grid cells at time t."""
    if t <= path[0][2]:
        return path[0][:2]
    for (x1, y1, t1), (x2, y2, t2) in zip(path, path[1:]):
        if t1 <= t < t2:
            f = (t - t1) / (t2 - t1)
            return (x1 + (x2 - x1) * f, y1 + (y2 - y1) * f)
    return path[-1][:2]


def headings_for(path):
    """Heading (degrees, 0 = right, 90 = down the screen) after each step."""
    headings = [0.0]
    for (x0, y0, _), (x1, y1, _) in zip(path, path[1:]):
        headings.append(DIRECTION_ANGLE.get((x1 - x0, y1 - y0), headings[-1]))
    return headings


def heading_at(path, headings, t):
    """Turn toward the new direction during the step that starts the turn."""
    for i, ((_, _, t1), (_, _, t2)) in enumerate(zip(path, path[1:])):
        if t1 <= t < t2:
            f = (t - t1) / (t2 - t1)
            a, b = headings[i], headings[i + 1]
            turn = (b - a + 180) % 360 - 180
            return a + turn * f
    return headings[-1] if t > path[0][2] else headings[0]


# =============================================================================
# 3. Tiny shape library (boxes and low-poly spheres, built from triangles)
# =============================================================================

def make_mesh(name, triangles, color):
    """triangles: list of (a, b, c) points. Flat-shaded, one color."""
    vdata = GeomVertexData(name, GeomVertexFormat.getV3n3c4(), Geom.UHStatic)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")
    prim = GeomTriangles(Geom.UHStatic)
    for i, (a, b, c) in enumerate(triangles):
        normal = (b - a).cross(c - a)
        normal.normalize()
        for p in (a, b, c):
            vw.addData3(p)
            nw.addData3(normal)
            cw.addData4(color)
        prim.addVertices(i * 3, i * 3 + 1, i * 3 + 2)
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def box(sx, sy, sz, color, name="box"):
    """Box centered on the origin, size sx * sy * sz."""
    x, y, z = sx / 2, sy / 2, sz / 2
    p = [Vec3(i, j, k) for i in (-x, x) for j in (-y, y) for k in (-z, z)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = []
    for a, b, c, d in faces:
        tris += [(p[a], p[b], p[c]), (p[a], p[c], p[d])]
    return make_mesh(name, tris, color)


def _icosphere(subdivisions):
    t = (1 + 5 ** 0.5) / 2
    verts = [Vec3(*v).normalized() for v in [
        (-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0),
        (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
        (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11),
             (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8),
             (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9),
             (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    for _ in range(subdivisions):
        cache, new_faces = {}, []

        def mid(i, j):
            key = (min(i, j), max(i, j))
            if key not in cache:
                verts.append(((verts[i] + verts[j]) / 2).normalized())
                cache[key] = len(verts) - 1
            return cache[key]

        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            new_faces += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = new_faces
    return verts, faces


def sphere(radius, color, subdivisions=1, roughness=0.0, seed=0,
           name="sphere"):
    """Low-poly sphere. roughness > 0 pushes vertices in and out (rocks)."""
    rng = random.Random(seed)
    verts, faces = _icosphere(subdivisions)
    bumps = [1 + rng.uniform(-roughness, roughness) for _ in verts]
    pts = [v * radius * k for v, k in zip(verts, bumps)]
    return make_mesh(name, [(pts[a], pts[b], pts[c]) for a, b, c in faces],
                     color)


def rock_island(parent, center, radius, seed, height=None):
    """A flattened rough rock with a grassy top and loose shore rocks."""
    height = height or min(radius * 0.35, 1.1)
    rock = sphere(1, ROCK, subdivisions=2, roughness=0.12, seed=seed)
    rock.reparentTo(parent)
    rock.setPos(center + Vec3(0, 0, -0.15))
    rock.setScale(radius, radius, height)
    top = sphere(1, GRASS, subdivisions=2, roughness=0.1, seed=seed + 10)
    top.reparentTo(parent)
    top.setPos(center + Vec3(radius * 0.1, radius * 0.08, height * 0.45))
    top.setScale(radius * 0.6, radius * 0.6, height * 0.6)
    for k in range(5):
        a = seed * 1.7 + k * 1.26
        pebble = sphere(0.25 + 0.06 * k, ROCK, roughness=0.2, seed=seed + k)
        pebble.reparentTo(parent)
        pebble.setPos(center + Vec3(math.cos(a) * radius,
                                    math.sin(a) * radius, 0))


# =============================================================================
# 4. The app
# =============================================================================

class Odyssey3D(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(NAVY)

        self.build_sea()
        self.build_ship()
        self.map_root = self.render.attachNewNode("map")      # per mode
        self.route_root = self.render.attachNewNode("route")
        self.kraken_root = self.render.attachNewNode("krakens")
        self.build_lights_and_camera()
        self.build_hud()

        self.accept("space", self.toggle_pause)
        self.accept("r", self.reset)
        self.accept("1", self.set_mode, ["sea"])
        self.accept("2", self.set_mode, ["demo"])
        self.accept("3", self.set_mode, ["voyage"])
        self.accept("n", self.new_map)
        self.arrow_order = []
        for name in ARROW_MOVES:
            self.accept(name, self.press_arrow, [name])
        self.accept("escape", self.userExit)

        self.mode = "sea"
        self.voyage_seed = 1
        self.build_world()
        self.taskMgr.add(self.update, "update")

    def press_arrow(self, name):
        if name in self.arrow_order:
            self.arrow_order.remove(name)
        self.arrow_order.append(name)

    # --- Sea: a grid mesh whose vertices bob up and down ---------------------

    SEA_W, SEA_D, SEA_STEP = 96, 72, 2       # size in units, vertex spacing

    def build_sea(self):
        nx, ny = self.SEA_W // self.SEA_STEP, self.SEA_D // self.SEA_STEP
        self.sea_data = GeomVertexData("sea", GeomVertexFormat.getV3n3c4(),
                                       Geom.UHDynamic)
        self.sea_data.setNumRows((nx + 1) * (ny + 1))
        self.sea_xy = []
        cw = GeomVertexWriter(self.sea_data, "color")
        for j in range(ny + 1):
            for i in range(nx + 1):
                self.sea_xy.append((i * self.SEA_STEP - self.SEA_W / 2,
                                    j * self.SEA_STEP - self.SEA_D / 2))
                cw.addData4(SEA)
        prim = GeomTriangles(Geom.UHStatic)
        for j in range(ny):
            for i in range(nx):
                a = j * (nx + 1) + i
                b, c, d = a + 1, a + nx + 1, a + nx + 2
                prim.addVertices(a, b, c)
                prim.addVertices(b, d, c)
        geom = Geom(self.sea_data)
        geom.addPrimitive(prim)
        node = GeomNode("sea")
        node.addGeom(geom)
        self.sea = self.render.attachNewNode(node)
        mat = Material()
        mat.setSpecular(Vec4(0.6, 0.6, 0.7, 1))
        mat.setShininess(40)
        self.sea.setMaterial(mat)
        self.animate_sea(0.0)

    def animate_sea(self, t):
        vw = GeomVertexWriter(self.sea_data, "vertex")
        nw = GeomVertexWriter(self.sea_data, "normal")
        for x, y in self.sea_xy:
            a1, a2 = x * 0.45 + t * 1.4, y * 0.6 - t * 1.1
            z = 0.12 * math.sin(a1) + 0.08 * math.sin(a2)
            vw.setData3(x, y, z)
            n = Vec3(-0.054 * math.cos(a1), -0.048 * math.cos(a2), 1)
            n.normalize()
            nw.setData3(n)

    # --- Per-mode map: SEA islands or the DEMO channel, plus Ithaca -----------

    def build_map(self):
        self.map_root.getChildren().detach()
        if self.mode == "demo":
            self.build_narrows()
        else:
            islands = (self.voyage.islands if self.mode == "voyage"
                       else scenario.ISLANDS)
            for i, (px, py, r) in enumerate(islands):
                rock_island(self.map_root, px_to_world(px, py),
                            r / scenario.CELL_SIZE, seed=i)
        self.build_ithaca()

    def build_narrows(self):
        """DEMO: land on both sides of the one-cell channel."""
        left = scenario.PASSAGE_START - 0.5
        right = scenario.PASSAGE_END + 0.5
        width = right - left
        mid_x = (left + right) / 2 - scenario.GRID_WIDTH / 2
        ch_y = cell_to_world(0, scenario.PASSAGE_Y).y
        depth = 7.0
        for side in (1, -1):                       # north bank, south bank
            y = ch_y + side * (0.5 + depth / 2)
            land = box(width, depth, 0.8, ROCK)
            land.reparentTo(self.map_root)
            land.setPos(mid_x, y, 0.2)
            grass = box(width - 0.6, depth - 1.2, 0.2, GRASS)
            grass.reparentTo(self.map_root)
            grass.setPos(mid_x, y + side * 0.4, 0.7)
            for k in range(int(width)):            # rocky edge on the channel
                stone = sphere(0.35, ROCK, roughness=0.25, seed=k * 2 + side)
                stone.reparentTo(self.map_root)
                stone.setPos(left + 0.5 + k - scenario.GRID_WIDTH / 2,
                             ch_y + side * 0.75, 0.35)
        label = TextNode("narrows")
        label.setText("THE NARROWS")
        label.setAlign(TextNode.ACenter)
        label.setTextColor(MUTED)
        text = self.map_root.attachNewNode(label)
        text.setPos(mid_x, ch_y + 4.5, 1.2)
        text.setScale(0.9)
        text.setBillboardPointEye()
        text.setLightOff()

    def build_ithaca(self):
        pos = cell_to_world(*scenario.GOAL) + Vec3(2.2, 0, 0)
        rock_island(self.map_root, pos, 1.7, seed=42, height=0.8)
        temple = self.map_root.attachNewNode("temple")
        temple.setPos(pos + Vec3(0, 0, 0.55))
        temple.setScale(1.3)
        box(1.0, 0.7, 0.12, WHITE).reparentTo(temple)
        for cx in (-0.38, -0.13, 0.13, 0.38):
            for cy in (-0.25, 0.25):
                col = box(0.08, 0.08, 0.5, WHITE)
                col.reparentTo(temple)
                col.setPos(cx, cy, 0.3)
        roof = box(1.1, 0.8, 0.12, GOLD)
        roof.reparentTo(temple)
        roof.setZ(0.6)
        cap = box(0.85, 0.55, 0.12, GOLD)
        cap.reparentTo(temple)
        cap.setZ(0.72)
        label = TextNode("ithaca-label")
        label.setText("ITHACA")
        label.setAlign(TextNode.ACenter)
        label.setTextColor(GOLD)
        text = temple.attachNewNode(label)
        text.setScale(0.5)
        text.setZ(1.3)
        text.setBillboardPointEye()
        text.setLightOff()

    # --- The ship: hull, ram, mast, square sail, oars (faces +x) --------------

    def build_ship(self):
        self.ship = self.render.attachNewNode("ship")
        body = self.ship.attachNewNode("body")
        body.setScale(1.4)
        hull = box(1.3, 0.4, 0.24, WOOD)
        hull.reparentTo(body)
        hull.setZ(0.12)
        bow = box(0.3, 0.3, 0.2, WOOD)
        bow.reparentTo(body)
        bow.setPos(0.72, 0, 0.14)
        bow.setH(45)
        stern = box(0.2, 0.36, 0.34, DARK_WOOD)
        stern.reparentTo(body)
        stern.setPos(-0.62, 0, 0.2)
        mast = box(0.06, 0.06, 1.1, DARK_WOOD)
        mast.reparentTo(body)
        mast.setZ(0.75)
        sail = box(0.04, 0.9, 0.65, WHITE)
        sail.reparentTo(body)
        sail.setPos(0.02, 0, 0.85)
        self.oars = []
        for k in range(4):
            for side in (-1, 1):
                pivot = body.attachNewNode("oar")
                pivot.setPos(-0.4 + k * 0.25, side * 0.2, 0.16)
                oar = box(0.035, 0.6, 0.035, DARK_WOOD)
                oar.reparentTo(pivot)
                oar.setPos(0, side * 0.3, -0.05)
                self.oars.append((pivot, side))

    # --- Krakens: tentacles that rise where each storm is ---------------------

    def build_krakens(self):
        self.kraken_root.getChildren().detach()
        self.krakens = []
        for hazard in self.hazards:
            node = self.kraken_root.attachNewNode("kraken")
            node.setPos(cell_to_world(*hazard["position"]))
            r = hazard["radius"]
            count = 5 + r * 2
            tentacles = []
            for k in range(count):
                segments = []
                for s in range(10):
                    seg = sphere(1, KRAKEN_RED, subdivisions=1, seed=s)
                    seg.reparentTo(node)
                    segments.append(seg)
                tentacles.append((k / count * math.tau, segments))
            # spread over the storm area; taller for bigger storms
            self.krakens.append((hazard, node, tentacles,
                                 0.25 + r * 0.7, 1.8 + r * 0.5))

    def update_krakens(self, t):
        for hazard, node, tentacles, ring, height in self.krakens:
            rise = scenario.hazard_rise(hazard, t)
            if rise <= 0:
                node.hide()
                continue
            node.show()
            node.setZ(-(height + 0.3) * (1 - rise))
            for angle, segments in tentacles:
                for s, seg in enumerate(segments):
                    f = s / (len(segments) - 1)
                    sway = 0.15 * math.sin(t * 2.2 + angle * 2 + f * 3)
                    out = ring + 0.4 * math.sin(f * math.pi * 0.8) + sway
                    seg.setPos(math.cos(angle) * out, math.sin(angle) * out,
                               f * height)
                    seg.setScale(0.17 * (1 - f * 0.7))

    # --- Route: small gold beads on the water (autopilot modes only) ----------

    def build_route(self):
        self.route_root.getChildren().detach()
        if self.mode == "voyage" or not self.path:
            return
        cells = []
        for x, y, _ in self.path:
            if not cells or cells[-1] != (x, y):
                cells.append((x, y))
        points = [cell_to_world(*c, z=0.15) for c in cells]
        for a, b in zip(points, points[1:]):
            for i in range(2):
                bead = sphere(0.07, GOLD)
                bead.reparentTo(self.route_root)
                bead.setPos(a + (b - a) * (i / 2))
        self.route_root.setLightOff()
        self.route_root.flattenStrong()

    # --- Light and camera -----------------------------------------------------

    def build_lights_and_camera(self):
        sun = DirectionalLight("sun")
        sun.setColor(Vec4(1.0, 0.95, 0.85, 1))
        sun.setShadowCaster(True, 2048, 2048)
        lens = sun.getLens()
        lens.setFilmSize(60, 45)
        lens.setNearFar(-40, 40)
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(35, -55, 0)
        self.render.setLight(sun_np)

        amb = AmbientLight("ambient")
        amb.setColor(Vec4(0.35, 0.38, 0.45, 1))
        self.render.setLight(self.render.attachNewNode(amb))
        self.render.setShaderAuto()

        self.camLens.setFov(55)
        self.camera.setPos(0, -33, 30)
        self.camera.lookAt(0, 0.5, 0)

    # --- HUD: the same text as main.py, plus the VOYAGE mode ------------------

    def build_hud(self):
        def text(parent, pos, scale, color, align=TextNode.ALeft):
            return OnscreenText(text="", parent=parent, pos=pos, scale=scale,
                                fg=color, align=align, mayChange=True)

        tl, tr, bl, br = (self.a2dTopLeft, self.a2dTopRight,
                          self.a2dBottomLeft, self.a2dBottomRight)
        text(tl, (0.08, -0.13), 0.11, GOLD).setText("ODYSSEY")
        text(tl, (0.085, -0.2), 0.04, MUTED).setText("THE FRACTURED SEA")
        self.mode_text = text(tl, (0.6, -0.1), 0.04, MUTED)
        self.status_text = text(tr, (-0.08, -0.1), 0.045, GOLD, TextNode.ARight)
        self.time_text = text(tr, (-0.08, -0.16), 0.045, WHITE, TextNode.ARight)
        self.steps_text = text(tr, (-0.08, -0.22), 0.04, MUTED, TextNode.ARight)
        self.message_text = OnscreenText(text="", pos=(0, 0.72), scale=0.05,
                                         fg=DANGER, mayChange=True)
        self.controls_text = text(bl, (0.08, 0.07), 0.04, WHITE)
        self.countdown_text = text(br, (-0.5, 0.07), 0.04, SAFE, TextNode.ARight)
        text(br, (-0.08, 0.07), 0.04, GOLD, TextNode.ARight).setText("ITHACA")

    # --- Modes and maps -------------------------------------------------------

    def set_mode(self, mode):
        if mode != self.mode:
            self.mode = mode
            self.build_world()

    def new_map(self):
        if self.mode == "voyage":
            self.voyage_seed += 1
            self.build_world()

    def build_world(self):
        if self.mode == "voyage":
            self.voyage = voyage.generate(self.voyage_seed, ChronosPlanner)
            self.hazards, self.path = self.voyage.hazards, self.voyage.path
        else:
            _obstacles, self.hazards, self.path = scenario.plan(
                ChronosPlanner, self.mode == "demo")
        self.navigator = Navigator(self.path)
        self.headings = headings_for(self.path) if self.path else [0.0]
        self.build_map()
        self.build_krakens()
        self.build_route()
        self.reset()

    def reset(self):
        """R: same map, back to the start."""
        self.simulation_time = 0.0          # in planner steps
        self.paused = True
        self.navigator.reset()
        # manual sailing state
        self.cell = scenario.START
        self.move_to = None                 # cell we are gliding into
        self.move_start = 0.0
        self.heading = 0.0
        self.turn_from = 0.0
        self.outcome = None                 # None, "WRECKED" or "ARRIVED"
        self.draw_frame()

    def toggle_pause(self):
        if self.mode == "voyage":
            if self.outcome is None and self.simulation_time > 0:
                self.paused = not self.paused
        elif self.path and not self.navigator.finished:
            self.paused = not self.paused

    # --- Every frame ----------------------------------------------------------

    def update(self, task):
        """Advance the clock (in planner steps), then place everything."""
        steps = globalClock.getDt() / STEP_SECONDS_3D  # noqa: F821
        if self.mode == "voyage":
            self.update_voyage(steps)
        elif not self.paused and self.path:
            self.simulation_time += steps
            self.navigator.update(self.simulation_time)
            if self.navigator.finished:
                self.paused = True
                self.simulation_time = self.path[-1][2]
        self.draw_frame()
        return task.cont

    def held_arrow(self):
        """The most recently pressed arrow key that is still held down."""
        down = self.mouseWatcherNode.isButtonDown
        for name in reversed(self.arrow_order):
            if down(ARROW_BUTTONS[name]):
                return name
        return None

    def update_voyage(self, steps):
        if self.outcome:
            return
        arrow = self.held_arrow()
        if self.paused:
            if arrow is None:
                return
            self.paused = False             # an arrow starts (or resumes)
            steps = 0.0                     # ...and the clock starts now
        self.simulation_time += steps
        t = self.simulation_time
        arrow = self.held_arrow()           # read the key at the new time

        next_start = t
        if self.move_to and t - self.move_start >= 1.0:   # finished a cell
            self.cell, self.move_to = self.move_to, None
            next_start = self.move_start + 1.0  # chain moves with no gap
            if self.cell == scenario.GOAL:      # arrive even if a key is held
                self.simulation_time = next_start
                self.outcome = "ARRIVED"
                return
        if self.move_to is None and arrow:
            dx, dy = ARROW_MOVES[arrow]
            target = (self.cell[0] + dx, self.cell[1] + dy)
            if (0 <= target[0] < scenario.GRID_WIDTH and
                    0 <= target[1] < scenario.GRID_HEIGHT and
                    target not in self.voyage.obstacles):
                self.move_to = target
                self.move_start = next_start
                self.turn_from = self.heading
                self.heading = DIRECTION_ANGLE[(dx, dy)]

        if voyage.hazard_hits(self.hazards, self.current_cell(), t):
            self.outcome = "WRECKED"
        elif self.move_to is None and self.cell == scenario.GOAL:
            self.outcome = "ARRIVED"

    def manual_position(self):
        if self.move_to is None:
            return self.cell, self.heading
        f = min(1.0, self.simulation_time - self.move_start)
        (x0, y0), (x1, y1) = self.cell, self.move_to
        turn = (self.heading - self.turn_from + 180) % 360 - 180
        return ((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f),
                self.turn_from + turn * f)

    def current_cell(self):
        """Old cell until halfway through a move, then the new one."""
        if self.move_to and self.simulation_time - self.move_start >= 0.5:
            return self.move_to
        return self.cell

    # --- Status text ----------------------------------------------------------

    def navigation_status(self):
        nav = self.navigator
        if not self.path:
            return "NO ROUTE"
        if nav.finished:
            return "ARRIVED"
        if self.paused:
            return "PAUSED"
        if nav.index + 1 < len(self.path):
            if self.path[nav.index][:2] == self.path[nav.index + 1][:2]:
                return "WAITING"
        return "SAILING"

    def captain_status(self):
        if self.outcome == "WRECKED":
            return "SHIPWRECKED"
        if self.outcome:
            return self.outcome
        if self.paused:
            return "READY" if self.simulation_time == 0 else "PAUSED"
        return "SAILING" if self.move_to else "HOLDING"

    def storm_active(self, t):
        hazard = self.hazards[0]
        return int(t) % hazard["period"] < hazard["active_duration"]

    def storm_countdown(self, t):
        hazard = self.hazards[0]
        phase = t % hazard["period"]
        if phase < hazard["active_duration"]:
            return "STORM CLEARS IN", hazard["active_duration"] - phase
        return "STORM RETURNS IN", hazard["period"] - phase

    # --- Draw -----------------------------------------------------------------

    def draw_frame(self):
        t = self.simulation_time
        self.animate_sea(t)
        self.update_krakens(t)

        if self.mode == "voyage":
            (gx, gy), heading = self.manual_position()
            status = self.captain_status()
            rowing = status == "SAILING"
        elif self.path:
            gx, gy = position_at(self.path, t)
            heading = heading_at(self.path, self.headings, t)
            status = self.navigation_status()
            rowing = status == "SAILING"
        else:
            (gx, gy), heading = scenario.START, 0.0
            status, rowing = self.navigation_status(), False

        self.ship.setPos(cell_to_world(gx, gy, z=0.05 * math.sin(t * 2.5)))
        # 0 = right, 90 = down the screen; Panda: +H turns left
        self.ship.setHpr(-heading, 0, 3 * math.sin(t * 1.7))
        stroke = 25 * math.sin(t * math.tau) if rowing else 0
        for pivot, side in self.oars:
            pivot.setH(stroke * side)

        if self.mode == "voyage":
            self.draw_voyage_hud(t, status)
        else:
            self.draw_autopilot_hud(t, status)

    def draw_autopilot_hud(self, t, status):
        seconds = t * STEP_SECONDS_3D
        self.mode_text.setText(
            "MODE: " + ("CHRONOS DEMO" if self.mode == "demo" else "CINEMATIC"))
        self.status_text.setText(f"CHRONOS ENGINE: {status}")
        self.time_text.setText(f"SIMULATION TIME: {seconds:06.1f}")
        remaining = (max(0, len(self.path) - self.navigator.index - 1)
                     if self.path else 0)
        self.steps_text.setText(f"ROUTE STEPS REMAINING: {remaining}")
        self.controls_text.setText(
            "SPACE: START / PAUSE    R: RESET    1: SEA  2: DEMO  3: VOYAGE")

        if status == "WAITING":
            self.show_message("POSEIDON BLOCKS THE PASSAGE — HOLD POSITION",
                              DANGER)
        elif status == "ARRIVED":
            self.show_message("MISSION COMPLETE — ITHACA REACHED", GOLD)
        elif status == "NO ROUTE":
            self.show_message("NO SAFE ROUTE — CHECK THE NAVIGATION MAP",
                              DANGER)
        else:
            self.show_message("", GOLD)

        label, countdown = self.storm_countdown(t)
        self.countdown_text.setText(
            f"{label}: {countdown * STEP_SECONDS_3D:.1f}s")
        self.countdown_text.setFg(DANGER if self.storm_active(t) else SAFE)

    def draw_voyage_hud(self, t, status):
        yours = t * STEP_SECONDS_3D
        best = self.voyage.chronos_steps * STEP_SECONDS_3D
        self.mode_text.setText(f"MODE: VOYAGE (MANUAL)   MAP #{self.voyage.seed}")
        self.status_text.setText(f"CAPTAIN: {status}")
        self.time_text.setText(f"YOUR TIME: {yours:06.1f}")
        self.steps_text.setText(f"CHRONOS TIME: {best:.1f}s")
        self.controls_text.setText(
            "ARROWS: SAIL   SPACE: PAUSE   R: RETRY   N: NEW MAP   "
            "1: SEA  2: DEMO  3: VOYAGE")
        self.countdown_text.setText("")

        if status == "SHIPWRECKED":
            self.show_message("SHIPWRECKED BY THE KRAKEN — PRESS R TO RETRY",
                              DANGER)
        elif status == "ARRIVED":
            verdict = ("YOU BEAT CHRONOS!" if yours < best - 1e-6 else
                       "YOU MATCHED CHRONOS!" if yours <= best + 1e-6 else
                       f"CHRONOS WAS {yours - best:.1f}s FASTER")
            self.show_message(f"ITHACA REACHED IN {yours:.1f}s — {verdict}",
                              GOLD)
        elif status == "READY":
            self.show_message("HOLD AN ARROW KEY TO SAIL — AVOID THE KRAKENS",
                              GOLD)
        else:
            self.show_message("", GOLD)

    def show_message(self, text, color):
        self.message_text.setText(text)
        self.message_text.setFg(color)


if __name__ == "__main__":
    Odyssey3D().run()
