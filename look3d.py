"""The night-sea look: sky, stars, sea strokes, islands, ship, monsters.

Everything is built from triangles and lines in code (no image files), in
the style of the ODYSSEY title screen: deep night sky, hazy horizon, dark
teal sea with pale wave strokes, faceted rock, a rust-red sail.
"""

import math
import os
import random

from panda3d.core import (
    Vec3, Vec4, NodePath, GeomVertexFormat, GeomVertexData, GeomVertexWriter,
    GeomTriangles, GeomPoints, Geom, GeomNode, LineSegs, Fog, AmbientLight,
    DirectionalLight, TransparencyAttrib, SamplerState,
)


def rgb(r, g, b, a=255):
    return Vec4(r / 255, g / 255, b / 255, a / 255)


SKY_TOP = rgb(10, 16, 28)
SKY_MID = rgb(22, 34, 46)
SKY_HORIZON = rgb(88, 108, 116)
HAZE = rgb(46, 66, 78)
SEA = rgb(20, 44, 58)
STROKE = rgb(120, 150, 160)
ROCK = rgb(78, 92, 94)
ROCK_DARK = rgb(44, 56, 60)
MOSS = rgb(44, 62, 52)
CLIFF_LIGHT = rgb(60, 84, 88)
HULL = rgb(26, 22, 18)
SAIL = rgb(176, 84, 58)
CREAM = rgb(232, 221, 190)
GOLD = rgb(196, 160, 100)
MUTED = rgb(170, 176, 172)
DANGER = rgb(214, 96, 84)
KRAKEN = rgb(112, 30, 44)
CYCLONE = rgb(170, 190, 200, 120)
BEAM = rgb(240, 210, 150, 46)
GULL = rgb(225, 228, 222)
FOAM = rgb(205, 222, 226)

FONT_DIR = "/System/Library/Fonts/Supplemental"


def load_font(base, name):
    """A system font if present (macOS), else Panda's default font."""
    path = os.path.join(FONT_DIR, name)
    if not os.path.exists(path):
        return None
    font = base.loader.loadFont(path)
    font.setPixelsPerUnit(120)
    font.setMinfilter(SamplerState.FT_linear_mipmap_linear)
    font.setMagfilter(SamplerState.FT_linear)
    return font


def spaced(text):
    return " ".join(text)


# --- geometry ------------------------------------------------------------------

def mesh(name, verts, colors, tris, normals=None, dynamic=False):
    vdata = GeomVertexData(name, GeomVertexFormat.getV3n3c4(),
                           Geom.UHDynamic if dynamic else Geom.UHStatic)
    vw = GeomVertexWriter(vdata, "vertex")
    nw = GeomVertexWriter(vdata, "normal")
    cw = GeomVertexWriter(vdata, "color")
    for i, v in enumerate(verts):
        vw.addData3(v)
        nw.addData3(normals[i] if normals else Vec3(0, 0, 1))
        cw.addData4(colors[i])
    prim = GeomTriangles(Geom.UHStatic)
    for a, b, c in tris:
        prim.addVertices(a, b, c)
    geom = Geom(vdata)
    geom.addPrimitive(prim)
    node = GeomNode(name)
    node.addGeom(geom)
    return NodePath(node)


def flat_mesh(name, triangles, color):
    """Flat-shaded triangles in one color (the faceted look)."""
    verts, cols, norms, tris = [], [], [], []
    for a, b, c in triangles:
        n = (b - a).cross(c - a)
        n.normalize()
        base = len(verts)
        verts += [a, b, c]
        cols += [color] * 3
        norms += [n] * 3
        tris.append((base, base + 1, base + 2))
    return mesh(name, verts, cols, tris, norms)


def box(sx, sy, sz, color, name="box"):
    x, y, z = sx / 2, sy / 2, sz / 2
    p = [Vec3(i, j, k) for i in (-x, x) for j in (-y, y) for k in (-z, z)]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    tris = []
    for a, b, c, d in faces:
        tris += [(p[a], p[b], p[c]), (p[a], p[c], p[d])]
    return flat_mesh(name, tris, color)


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


def sphere(radius, color, subdivisions=1, roughness=0.0, seed=0):
    rng = random.Random(seed)
    verts, faces = _icosphere(subdivisions)
    pts = [v * radius * (1 + rng.uniform(-roughness, roughness))
           for v in verts]
    return flat_mesh("sphere", [(pts[a], pts[b], pts[c])
                                for a, b, c in faces], color)


def lines(name, color, thickness, polylines):
    segs = LineSegs(name)
    segs.setThickness(thickness)
    segs.setColor(color)
    for pts in polylines:
        segs.moveTo(pts[0])
        for p in pts[1:]:
            segs.drawTo(p)
    np = NodePath(segs.create())
    np.setLightOff()
    return np


def translucent(np, depth_write=False):
    np.setTransparency(TransparencyAttrib.MAlpha)
    np.setDepthWrite(depth_write)
    np.setBin("transparent", 10)
    return np


# --- sky, stars, light, haze ---------------------------------------------------

def build_sky(camera):
    rings, segs, radius = 24, 48, 400.0
    verts, cols, tris = [], [], []
    for i in range(rings + 1):
        elev = -0.15 + (math.pi / 2 + 0.15) * i / rings
        for j in range(segs + 1):
            az = math.tau * j / segs
            verts.append(Vec3(math.cos(elev) * math.cos(az) * radius,
                              math.cos(elev) * math.sin(az) * radius,
                              math.sin(elev) * radius))
            h = max(0.0, math.sin(elev))
            if h < 0.12:
                f = h / 0.12
                c = SKY_HORIZON * (1 - f) + SKY_MID * f
            else:
                f = min(1.0, (h - 0.12) / 0.5)
                c = SKY_MID * (1 - f) + SKY_TOP * f
            c.w = 1
            cols.append(c)
    for i in range(rings):
        for j in range(segs):
            a = i * (segs + 1) + j
            b, c, d = a + 1, a + segs + 1, a + segs + 2
            tris += [(a, c, b), (b, c, d)]
    sky = mesh("sky", verts, cols, tris)
    sky.reparentTo(camera)
    sky.setCompass()
    sky.setBin("background", 0)
    sky.setDepthWrite(False)
    sky.setLightOff()
    sky.setFogOff()
    sky.setTwoSided(True)

    rng = random.Random(7)
    vdata = GeomVertexData("stars", GeomVertexFormat.getV3c4(), Geom.UHStatic)
    vw = GeomVertexWriter(vdata, "vertex")
    cw = GeomVertexWriter(vdata, "color")
    pts = GeomPoints(Geom.UHStatic)
    for n in range(900):
        az = rng.uniform(0, math.tau)
        elev = math.asin(rng.uniform(0.04, 1.0))
        vw.addData3(math.cos(elev) * math.cos(az) * 380,
                    math.cos(elev) * math.sin(az) * 380,
                    math.sin(elev) * 380)
        b = rng.uniform(0.35, 1.0) * min(1.0, elev / 0.3)
        cw.addData4(b, b, b * 0.95, 1)
        pts.addVertex(n)
    geom = Geom(vdata)
    geom.addPrimitive(pts)
    node = GeomNode("stars")
    node.addGeom(geom)
    stars = camera.attachNewNode(node)
    stars.setCompass()
    stars.setBin("background", 1)
    stars.setDepthWrite(False)
    stars.setLightOff()
    stars.setFogOff()
    stars.setRenderModeThickness(2)
    return sky, stars


def build_light_and_fog(render, density=0.0105):
    moon = DirectionalLight("moon")
    moon.setColor(Vec4(0.55, 0.62, 0.7, 1))
    mn = render.attachNewNode(moon)
    mn.setHpr(25, -35, 0)          # from behind the viewer, high
    render.setLight(mn)
    amb = AmbientLight("amb")
    amb.setColor(Vec4(0.28, 0.32, 0.38, 1))
    render.setLight(render.attachNewNode(amb))
    fog = Fog("haze")
    fog.setColor(HAZE)
    fog.setExpDensity(density)
    render.setFog(fog)
    render.setShaderAuto()
    return fog


# --- sea -----------------------------------------------------------------------

STROKE_TILE = (140.0, 120.0)      # world size of one repeating stroke tile


def build_sea(render, count=1100):
    """Dark water plus pale wave strokes. The strokes live in one tile that
    is repeated 3x3 around the camera (see place_sea_tiles), so the sea
    goes on forever. Returns (sea, layers, tiles)."""
    size = 4000
    verts = [Vec3(-size, -size, 0), Vec3(size, -size, 0),
             Vec3(-size, size, 0), Vec3(size, size, 0)]
    sea = mesh("sea", verts, [SEA] * 4, [(0, 1, 2), (1, 3, 2)])
    sea.reparentTo(render)
    rng = random.Random(11)
    tile = NodePath("stroke-tile")
    tw, th = STROKE_TILE
    layers = []
    for _ in range(2):
        segs = LineSegs("strokes")
        segs.setThickness(1.6)
        for _ in range(count):
            x, y = rng.uniform(0, tw), rng.uniform(0, th)
            length = rng.uniform(0.6, 2.8)
            segs.setColor(STROKE.x, STROKE.y, STROKE.z, rng.uniform(0.25, 0.8))
            segs.moveTo(x, y, 0.02)
            segs.drawTo(x + length, y, 0.02)
        np = tile.attachNewNode(segs.create())
        layers.append(np)
    tile.setLightOff()
    tile.setTransparency(TransparencyAttrib.MAlpha)
    tiles = []
    for _ in range(9):
        holder = render.attachNewNode("stroke-holder")
        tile.instanceTo(holder)
        tiles.append(holder)
    return sea, layers, tiles


def place_sea_tiles(tiles, cam_x, cam_y):
    tw, th = STROKE_TILE
    kx, ky = math.floor(cam_x / tw), math.floor(cam_y / th)
    i = 0
    for dx in (-1, 0, 1):
        for dy in (0, 1, 2):
            tiles[i].setPos((kx + dx) * tw - tw / 2, (ky + dy) * th - 10, 0)
            i += 1


def animate_strokes(layers, t):
    for i, layer in enumerate(layers):
        layer.setX(math.sin(t * 0.35 + i * 2.1) * 1.2)
        layer.setY(math.sin(t * 0.25 + i) * 1.5)
        layer.setAlphaScale(0.55 + 0.45 * math.sin(t * 0.8 + i * math.pi))


def rough_patch(radius, seed):
    """Churning water: a dark swirl, spinning foam arcs, bobbing whitecaps.
    Returns (node, spin, caps)."""
    rng = random.Random(seed)
    node = NodePath("rough")
    n = 28
    verts = [Vec3(0, 0, 0.03)] + [
        Vec3(math.cos(math.tau * i / n) * radius * rng.uniform(0.9, 1.1),
             math.sin(math.tau * i / n) * radius * rng.uniform(0.9, 1.1), 0.03)
        for i in range(n + 1)]
    disc = mesh("churn", verts, [rgb(12, 26, 36)] + [rgb(16, 36, 48)] * (n + 1),
                [(0, i, i + 1) for i in range(1, n + 1)])
    disc.reparentTo(node)
    disc.setLightOff()
    spin = node.attachNewNode("spin")
    arcs = []
    for ring in range(4):
        r = radius * (0.25 + ring * 0.22)
        start = rng.uniform(0, math.tau)
        for part in range(3):
            a0 = start + part * math.tau / 3
            arcs.append([Vec3(math.cos(a0 + k * 0.12) * r,
                              math.sin(a0 + k * 0.12) * r, 0.08)
                         for k in range(12)])
    lines("foam", FOAM, 2.2, arcs).reparentTo(spin)
    caps = []
    for k in range(int(10 + radius * 3)):
        a, r = rng.uniform(0, math.tau), radius * rng.uniform(0.15, 0.95)
        cap = sphere(rng.uniform(0.12, 0.26), FOAM, subdivisions=1, seed=k)
        cap.reparentTo(node)
        cap.setPos(math.cos(a) * r, math.sin(a) * r, 0.05)
        cap.setLightOff()
        caps.append((cap, rng.uniform(0, math.tau)))
    return node, spin, caps


def animate_rough(spin, caps, t):
    spin.setH(t * 70)
    for cap, phase in caps:
        cap.setZ(0.05 + 0.25 * max(0.0, math.sin(t * 5 + phase)))


# --- land ----------------------------------------------------------------------

def build_cliff(render, x0=34.0, y0=110.0):
    """The tall faceted cliff of the title screen (scenery)."""
    ridge = [(0, 0), (2.5, 9), (5, 7.5), (8, 14), (11, 12), (14, 19),
             (17, 16.5), (20, 21), (26, 18), (32, 0)]
    front, back = y0, y0 + 12
    tris = []
    for (ax, az), (bx, bz) in zip(ridge, ridge[1:]):
        a_f, b_f = Vec3(x0 + ax, front, az), Vec3(x0 + bx, front, bz)
        a_g, b_g = Vec3(x0 + ax, front, 0), Vec3(x0 + bx, front, 0)
        a_b, b_b = Vec3(x0 + ax, back, az), Vec3(x0 + bx, back, bz)
        tris += [(a_g, b_g, b_f), (a_g, b_f, a_f), (a_f, b_f, b_b),
                 (a_f, b_b, a_b)]
    cliff = flat_mesh("cliff", tris, ROCK_DARK)
    cliff.reparentTo(render)
    streaks = [[Vec3(x0 + 3 + k * 1.9, front - 0.05, 0.6),
                Vec3(x0 + 3.4 + k * 1.9, front - 0.05,
                     min(18, 4 + k * 1.3) * 0.7)] for k in range(14)]
    lines("streaks", CLIFF_LIGHT, 1.2, streaks).reparentTo(cliff)
    return cliff


def island(radius, height, seed, color=ROCK):
    """A faceted rocky island: jagged rings rising to a peak."""
    rng = random.Random(seed)
    n = 14
    rings = [(radius * 1.05, 0.0), (radius * 0.8, height * 0.45),
             (radius * 0.45, height * 0.85)]
    ring_pts = []
    for r, z in rings:
        ring_pts.append([Vec3(math.cos(math.tau * i / n) * r *
                              rng.uniform(0.8, 1.15),
                              math.sin(math.tau * i / n) * r *
                              rng.uniform(0.8, 1.15),
                              z * rng.uniform(0.85, 1.15)) for i in range(n)])
    peak = Vec3(rng.uniform(-0.3, 0.3) * radius, rng.uniform(-0.3, 0.3) * radius,
                height)
    tris = []
    for lower, upper in zip(ring_pts, ring_pts[1:]):
        for i in range(n):
            a, b = lower[i], lower[(i + 1) % n]
            c, d = upper[i], upper[(i + 1) % n]
            tris += [(a, b, d), (a, d, c)]
    top = ring_pts[-1]
    for i in range(n):
        tris.append((top[i], top[(i + 1) % n], peak))
    node = flat_mesh("island", tris, color)
    for k in range(6):                      # rocks along the shore
        a = rng.uniform(0, math.tau)
        rock = sphere(rng.uniform(0.35, 0.8), ROCK_DARK, roughness=0.3,
                      seed=seed * 10 + k)
        rock.reparentTo(node)
        rock.setPos(math.cos(a) * radius * 1.1, math.sin(a) * radius * 1.1,
                    0.1)
    return node


def temple(scale=1.0):
    """A small pale temple with a gold roof (for Ithaca)."""
    root = NodePath("temple")
    box(1.6, 1.1, 0.16, CREAM).reparentTo(root)
    for cx in (-0.6, -0.2, 0.2, 0.6):
        for cy in (-0.4, 0.4):
            col = box(0.12, 0.12, 0.8, CREAM)
            col.reparentTo(root)
            col.setPos(cx, cy, 0.48)
    roof = box(1.8, 1.3, 0.18, GOLD)
    roof.reparentTo(root)
    roof.setZ(0.97)
    cap = box(1.3, 0.85, 0.18, GOLD)
    cap.reparentTo(root)
    cap.setZ(1.15)
    root.setScale(scale)
    return root


def reef(radius, seed):
    return sphere(radius, ROCK_DARK, subdivisions=1, roughness=0.35, seed=seed)


# --- ship ----------------------------------------------------------------------

def ship():
    """Dark hull, mast, rust-red sail, oars; faces +x. Returns (node, oars)."""
    root = NodePath("ship")
    h = [Vec3(-1.8, -0.3, 0.25), Vec3(1.5, -0.3, 0.25), Vec3(2.2, 0, 0.75),
         Vec3(-1.8, 0.3, 0.25), Vec3(1.5, 0.3, 0.25), Vec3(-1.5, 0, -0.1),
         Vec3(1.2, 0, -0.1)]
    tris = [(h[0], h[1], h[6]), (h[0], h[6], h[5]), (h[3], h[5], h[6]),
            (h[3], h[6], h[4]), (h[1], h[2], h[6]), (h[4], h[6], h[2]),
            (h[0], h[3], h[1]), (h[1], h[3], h[4])]
    flat_mesh("hull", tris, HULL).reparentTo(root)
    lines("prow", HULL, 2, [[Vec3(2.2, 0, 0.75), Vec3(2.6, 0, 1.15)]]
          ).reparentTo(root)
    lines("mast", HULL, 2.5, [[Vec3(0, 0, 0.25), Vec3(0, 0, 4.6)]]
          ).reparentTo(root)
    lines("rigging", HULL, 1, [[Vec3(0, 0, 4.6), Vec3(2.1, 0, 0.75)],
                               [Vec3(0, 0, 4.6), Vec3(-1.6, 0, 0.3)]]
          ).reparentTo(root)
    s = [Vec3(0.05, -1.1, 4.3), Vec3(0.05, 1.1, 4.3), Vec3(0.35, 0.95, 1.5),
         Vec3(0.35, -0.95, 1.5)]
    sail = flat_mesh("sail", [(s[0], s[1], s[2]), (s[0], s[2], s[3])], SAIL)
    sail.setTwoSided(True)
    sail.reparentTo(root)
    oars = []
    for k in range(4):
        for side in (-1, 1):
            pivot = root.attachNewNode("oar")
            pivot.setPos(-1.0 + k * 0.6, side * 0.3, 0.3)
            lines("oar", HULL, 1.5, [[Vec3(0, 0, 0),
                                      Vec3(0, side * 1.3, -0.45)]]
                  ).reparentTo(pivot)
            oars.append((pivot, side))
    return root, oars


# --- monsters and omens --------------------------------------------------------

def kraken(radius_cells, cell_size):
    """Tentacles around a center. Returns (node, tentacles, ring, height)."""
    node = NodePath("kraken")
    count = 5 + radius_cells * 2
    tentacles = []
    for k in range(count):
        segs = []
        for s in range(10):
            seg = sphere(1, KRAKEN, subdivisions=1, seed=s)
            seg.reparentTo(node)
            segs.append(seg)
        tentacles.append((k / count * math.tau, segs))
    ring = (0.4 + radius_cells * 0.8) * cell_size / 2
    height = 3.2 + radius_cells
    return node, tentacles, ring, height


def place_tentacles(tentacles, ring, height, t):
    for angle, segs in tentacles:
        for s, seg in enumerate(segs):
            f = s / (len(segs) - 1)
            sway = 0.3 * math.sin(t * 2.2 + angle * 2 + f * 3)
            out = ring + 0.7 * math.sin(f * math.pi * 0.8) + sway
            seg.setPos(math.cos(angle) * out, math.sin(angle) * out,
                       f * height)
            seg.setScale(0.32 * (1 - f * 0.7))


def cyclone():
    """A pale funnel of spinning rings."""
    node = NodePath("cyclone")
    spin = node.attachNewNode("spin")
    polys = []
    for k in range(9):
        z = k * 1.0
        r = 0.6 + (k / 8) ** 1.6 * 4.2
        pts = [Vec3(math.cos(a / 24 * math.tau) * r,
                    math.sin(a / 24 * math.tau) * r,
                    z + 0.4 * math.sin(a / 24 * math.tau * 2 + k))
               for a in range(25)]
        polys.append(pts)
    rings = lines("cyclone-rings", CYCLONE, 2, polys)
    rings.reparentTo(spin)
    translucent(rings)
    spokes = lines("cyclone-spokes", CYCLONE, 1, [
        [Vec3(math.cos(a) * (0.6 + (k / 8) ** 1.6 * 4.2),
              math.sin(a) * (0.6 + (k / 8) ** 1.6 * 4.2), k) for k in range(9)]
        for a in [i / 6 * math.tau for i in range(6)]])
    spokes.reparentTo(spin)
    translucent(spokes)
    return node, spin


def gulls(count=5):
    """White V-shaped birds; rotate the returned node to circle them."""
    node = NodePath("gulls")
    for k in range(count):
        a = k / count * math.tau
        r = 3.0 + (k % 2) * 0.8
        x, y, z = math.cos(a) * r, math.sin(a) * r, 7 + (k % 3) * 0.7
        g = lines("gull", GULL, 2, [[Vec3(x - 0.5, y, z + 0.25),
                                     Vec3(x, y, z), Vec3(x + 0.5, y, z + 0.25)]])
        g.reparentTo(node)
        g.setFogOff()
    return node


def beam(height=40.0):
    """A soft column of light from the sky (Athena's sign)."""
    n, r = 16, 1.6
    tris = []
    for i in range(n):
        a, b = math.tau * i / n, math.tau * (i + 1) / n
        p0 = Vec3(math.cos(a) * r, math.sin(a) * r, 0)
        p1 = Vec3(math.cos(b) * r, math.sin(b) * r, 0)
        tris += [(p0, p1, p1 + Vec3(0, 0, height)),
                 (p0, p1 + Vec3(0, 0, height), p0 + Vec3(0, 0, height))]
    node = flat_mesh("beam", tris, BEAM)
    node.setTwoSided(True)
    node.setLightOff()
    node.setFogOff()
    translucent(node)
    return node
