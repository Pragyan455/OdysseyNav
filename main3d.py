"""ODYSSEY | The Fractured Sea: the voyage home, in 3D (Panda3D).

Eight legs from Troy to Ithaca. On each leg only two islands rise from the
mist ahead. Read the omen, pick one, and sail there yourself with the arrow
keys past the krakens. Each island is an episode of the Odyssey with a
choice to make. Keep food, health, crew and the favor of the gods above
zero. If favor runs low, Poseidon's cyclone hunts you; if it catches you,
you are lost at sea until you find your way by the stars.

Run:  .venv/bin/python main3d.py
Keys: ENTER begin · ARROWS sail · SPACE pause / continue · 1 2 choose
      R restart voyage · N new voyage · ESC quit
Rules: core/journey.py   Story text: core/islands.py   Look: look3d.py
"""

import math
import os
import random

from panda3d.core import (
    loadPrcFileData, Vec3, Vec4, KeyboardButton, TextNode,
    TransparencyAttrib,
)

loadPrcFileData("", "win-size 1280 760\nwindow-title ODYSSEY | The Fractured Sea"
                    "\nframebuffer-multisample 1\nmultisamples 4")
if os.environ.get("ODYSSEY_MUTE"):
    loadPrcFileData("", "audio-library-name null")

from direct.showbase.ShowBase import ShowBase  # noqa: E402
from direct.gui.OnscreenText import OnscreenText  # noqa: E402

import look3d as L  # noqa: E402
from sound3d import Sound  # noqa: E402
from core import journey as J  # noqa: E402
from core import islands as I  # noqa: E402
from core.cyclone import Cyclone  # noqa: E402
from core.starpuzzle import StarPuzzle  # noqa: E402

CELL = 2.0                                   # world units per grid cell
ARROW_MOVES = {"arrow_up": (0, 1), "arrow_down": (0, -1),
               "arrow_left": (-1, 0), "arrow_right": (1, 0)}
ARROW_BUTTONS = {"arrow_up": KeyboardButton.up(),
                 "arrow_down": KeyboardButton.down(),
                 "arrow_left": KeyboardButton.left(),
                 "arrow_right": KeyboardButton.right()}
HEADING = {(1, 0): 0.0, (0, 1): 90.0, (-1, 0): 180.0, (0, -1): -90.0}
TITLE_CAM = (Vec3(0, -26, 3.2), Vec3(0, 60, 4.2))
LOW = {"food": 8, "health": 3, "crew": 4, "favor": 3}
DEPART_SECONDS = 2.6          # sailing around the island you landed on


def to_world(gx, gy, z=0.0):
    return Vec3((gx - (J.WIDTH - 1) / 2) * CELL, gy * CELL, z)


def effects_text(effects):
    parts = [f"{'+' if v > 0 else '-'}{abs(round(v))} {k.upper()}"
             for k, v in effects.items() if round(v) != 0]
    return "     ".join(parts) if parts else "NOTHING GAINED, NOTHING LOST"


class Odyssey(ShowBase):

    def __init__(self):
        super().__init__()
        self.disableMouse()
        self.setBackgroundColor(L.SKY_TOP)
        self.serif = L.load_font(self, "Georgia.ttf")
        self.italic = L.load_font(self, "Georgia Italic.ttf") or self.serif
        self.mono = L.load_font(self, "Courier New Bold.ttf")

        self.sky, self.stars = L.build_sky(self.camera)
        self.sea, self.strokes, self.sea_tiles = L.build_sea(self.render)
        self.cliff = L.build_cliff(self.render)
        L.build_light_and_fog(self.render, density=0.012)
        self.ship, self.oars = L.ship()
        self.ship.reparentTo(self.render)
        self.ship.setScale(0.6)
        self.leg_root = self.render.attachNewNode("leg")
        self.behind_root = self.render.attachNewNode("behind")  # last isle
        self.cyclone_node, self.cyclone_spin = L.cyclone()
        self.cyclone_node.reparentTo(self.render)

        self.sound = Sound(self, os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".sound_cache"))
        self.ending = None

        self.build_title()
        self.build_hud()
        self.build_card()
        self.build_star_chart()

        self.accept("enter", self.on_enter)
        self.accept("space", self.on_space)
        self.accept("mouse1", self.on_click)
        self.accept("1", self.choose, [0])
        self.accept("2", self.choose, [1])
        self.accept("r", self.restart_voyage)
        self.accept("n", self.new_voyage)
        self.accept("escape", self.userExit)
        self.arrow_order = []
        for name in ARROW_MOVES:
            self.accept(name, self.press_arrow, [name])

        self.anim_time = 0.0
        self.cam_pos, self.cam_look = Vec3(TITLE_CAM[0]), Vec3(TITLE_CAM[1])
        self.seed = 1
        self.state = "title"
        self.offset = Vec3(0, 0, 0)       # where this leg sits in the world
        self.new_journey()
        self.taskMgr.add(self.update, "update")

    # =========================================================================
    # Journey and legs
    # =========================================================================

    def new_journey(self):
        self.journey = J.Journey(self.seed)
        self.offset = Vec3(0, 0, 0)
        self.behind_root.getChildren().detach()
        troy = L.island(8.0, 5.0, seed=99)          # where the voyage begins
        troy.reparentTo(self.behind_root)
        troy.setPos(self.w(J.START[0], -6))
        self.behind_cells = []                      # grid cells it covers
        self.start_leg()

    def w(self, gx, gy, z=0.0):
        """Grid cell of the current leg -> world position."""
        return to_world(gx, gy, z) + self.offset

    def restart_voyage(self):
        if self.state != "title":
            self.state = "sail"
            self.new_journey()

    def new_voyage(self):
        if self.state != "title":
            self.seed += 1
            self.state = "sail"
            self.new_journey()

    def start_leg(self):
        j = self.journey
        self.leg = j.leg()
        self.rng = random.Random(self.seed * 7919 + j.leg_index)
        self.omen = ("final" if self.leg.final
                     else J.omen_level(j.resources["favor"]))
        # sailing state; time on a leg is counted in planner steps
        self.sim = 0.0
        self.cell = J.START
        self.move_to = None
        self.move_start = 0.0
        self.heading = 90.0
        self.turn_from = 90.0
        self.started = False
        self.paused = False
        self.invulnerable_until = -1.0
        self.flash, self.flash_until = "", 0.0
        self.puzzle = None
        self.chart_root.hide()
        self.cyclone = None
        if self.omen == "vague":
            self.cyclone = Cyclone(*J.cyclone_spawn(self.rng, J.START))
        self.rough = ([] if self.leg.final else
                      J.rough_water(self.leg, j.resources["favor"], self.rng))
        self.rough_cells = 0
        self.block_island_behind()
        self.build_leg()
        if self.rough and self.state != "title":
            self.show_flash("THE SEA GROWS ROUGH AS THE GODS TURN AWAY")
        self.kraken_up = [False] * len(self.krakens)
        self.star_seen = 0
        self.ending = None
        self.card_root.hide()
        if self.state != "title":
            self.state = "sail"

    def build_leg(self):
        self.leg_root.getChildren().detach()
        self.gull_nodes = []
        self.island_nodes = []
        for k, isle in enumerate(self.leg.islands):
            pos = self.w(*isle.center)
            rng = random.Random(self.seed * 31 + self.leg.index * 3 + k)
            node = L.island(isle.radius * CELL, rng.uniform(6.0, 9.5),
                            seed=rng.randint(0, 9999))
            node.reparentTo(self.leg_root)
            node.setPos(pos)
            self.island_nodes.append(node)
            if isle.final:
                t = L.temple(1.8)
                t.reparentTo(node)
                t.setZ(5.5)
            show_gulls = ((self.omen in ("clear", "subtle") and isle.correct)
                          or self.omen == "vague")
            if show_gulls:
                g = L.gulls()
                g.reparentTo(self.leg_root)
                g.setPos(pos)
                self.gull_nodes.append(g)
            if (self.omen == "clear" and isle.correct) or isle.final:
                b = L.beam()
                b.reparentTo(self.leg_root)
                b.setPos(pos + Vec3(0, 0, 2))
                self.label_3d(isle.name, pos + Vec3(0, 0, 11))

        for k, (gx, gy, r) in enumerate(self.leg.reefs):
            rock = L.reef(r * CELL * 0.75, seed=self.leg.index * 50 + k)
            rock.reparentTo(self.leg_root)
            rock.setPos(self.w(gx, gy, 0.2))

        self.krakens = []
        for hazard in self.leg.hazards:
            node, tentacles, ring, height = L.kraken(hazard["radius"], CELL)
            node.reparentTo(self.leg_root)
            node.setPos(self.w(*hazard["position"]))
            self.krakens.append((hazard, node, tentacles, ring, height))

        self.rough_nodes = []
        for k, (gx, gy, r) in enumerate(self.rough):
            node, spin, caps = L.rough_patch(r * CELL, seed=self.leg.index * 7 + k)
            node.reparentTo(self.leg_root)
            node.setPos(self.w(gx, gy))
            self.rough_nodes.append((spin, caps))

    def block_island_behind(self):
        """The island you just left still stands right behind the ship."""
        if not self.behind_cells:
            return
        (cx, cy), radius = self.behind_cells
        for x in range(J.WIDTH):
            for y in range(J.LENGTH):
                p = to_world(x, y) + self.offset
                if (Vec3(p.x - cx, p.y - cy, 0)).length() < radius:
                    self.leg.obstacles.add((x, y))

    def label_3d(self, text, pos):
        node = TextNode("label")
        node.setText(text)
        node.setAlign(TextNode.ACenter)
        node.setTextColor(L.CREAM)
        if self.serif:
            node.setFont(self.serif)
        np = self.leg_root.attachNewNode(node)
        np.setPos(pos)
        np.setScale(0.95)
        np.setBillboardPointEye()
        np.setLightOff()
        np.setFogOff()

    # =========================================================================
    # Input
    # =========================================================================

    def press_arrow(self, name):
        if name in self.arrow_order:
            self.arrow_order.remove(name)
        self.arrow_order.append(name)

    def held_arrow(self):
        down = self.mouseWatcherNode.isButtonDown
        for name in reversed(self.arrow_order):
            if down(ARROW_BUTTONS[name]):
                return name
        return None

    def on_enter(self):
        if self.state == "title":
            self.begin()
        elif self.state == "card":
            self.on_space()

    def on_space(self):
        if self.state == "title":
            self.begin()
        elif self.state == "sail" and self.started:
            self.paused = not self.paused
        elif self.state == "card" and self.card_phase == "result":
            self.depart()

    def on_click(self):
        if self.state == "title":
            self.begin()
        elif self.state == "lost" and self.mouseWatcherNode.hasMouse():
            m = self.mouseWatcherNode.getMouse()
            result = self.puzzle.click(m.x * self.getAspectRatio(), m.y)
            if result in ("ok", "solved"):
                self.sound.play("chime", 0.7)
            elif result == "wrong":
                self.sound.play("chime_low", 0.8)

    def begin(self):
        self.state = "sail"
        self.title_root.hide()

    # =========================================================================
    # Every frame
    # =========================================================================

    def update(self, task):
        dt = min(globalClock.getDt(), 0.1)  # noqa: F821
        self.anim_time += dt
        if self.state == "sail":
            self.update_sailing(dt)
        elif self.state == "lost":
            self.update_lost(dt)
        elif self.state == "depart":
            self.update_depart(dt)
        self.draw(dt)
        self.update_sound(dt)
        return task.cont

    def update_sailing(self, dt):
        arrow = self.held_arrow()
        if not self.started:
            if arrow is None:
                return
            self.started = True
            dt = 0.0
        if self.paused:
            return
        j = self.journey
        steps = dt / J.step_seconds(j.resources["crew"])
        self.sim += steps
        j.eat(dt)
        t = self.sim
        arrow = self.held_arrow()

        next_start = t
        if self.move_to and t - self.move_start >= 1.0:
            self.cell, self.move_to = self.move_to, None
            next_start = self.move_start + 1.0
            island = self.leg.landed(self.cell)
            if island:
                self.land(island)
                return
            if J.in_rough_water(self.rough, self.cell):
                self.rough_cells += 1
                if self.rough_cells % J.ROUGH_CELLS_PER_DAMAGE == 0:
                    j.apply({"health": -1})
                    self.show_flash("ROUGH WATER   -1 HEALTH")
                    self.sound.play("splash", 0.6)
        if self.move_to is None and arrow:
            dx, dy = ARROW_MOVES[arrow]
            target = (self.cell[0] + dx, self.cell[1] + dy)
            if self.leg.open(target):
                self.move_to, self.move_start = target, next_start
                self.turn_from, self.heading = self.heading, HEADING[(dx, dy)]

        if (t >= self.invulnerable_until and
                J.hazard_hits(self.leg.hazards, self.current_cell(), t)):
            j.apply(J.KRAKEN_DAMAGE)
            self.invulnerable_until = t + J.INVULNERABLE_STEPS
            self.sound.play("roar", 1.0)
            self.sound.play("splash", 0.9)
            self.show_flash("THE KRAKEN STRIKES   -3 HEALTH   -1 CREW")

        if self.cyclone:
            (sx, sy), _ = self.ship_position()
            self.cyclone.chase(sx, sy, steps)
            if self.cyclone.hits(sx, sy):
                self.get_lost()
                return
        self.check_game_over()

    def current_cell(self):
        if self.move_to and self.sim - self.move_start >= 0.5:
            return self.move_to
        return self.cell

    def ship_position(self):
        if self.move_to is None:
            return self.cell, self.heading
        f = min(1.0, self.sim - self.move_start)
        (x0, y0), (x1, y1) = self.cell, self.move_to
        turn = (self.heading - self.turn_from + 180) % 360 - 180
        return ((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f),
                self.turn_from + turn * f)

    def update_sound(self, dt):
        if self.state == "title" or self.ending == "won":
            music = "title"                      # the ancient Seikilos song
        elif self.ending == "over":
            music = None
        elif self.cyclone:
            music = "storm"
        else:
            music = "sea"
        wind = 0.0
        if self.cyclone and self.state in ("sail", "lost"):
            (sx, sy), _ = self.ship_position()
            d = math.hypot(sx - self.cyclone.x, sy - self.cyclone.y)
            wind = max(0.0, min(1.0, 1 - (d - 2) / 18)) * 0.9
        if self.state == "lost":
            wind = max(wind, 0.5)
        if self.state == "sail" and J.in_rough_water(self.rough,
                                                     self.current_cell()):
            wind = max(wind, 0.3)
        self.sound.update(dt, music, wind)
        # a roar and a splash when a kraken near the ship breaks the surface
        if self.state == "sail":
            (sx, sy), _ = self.ship_position()
            for k, (hazard, *_rest) in enumerate(self.krakens):
                up = J.hazard_rise(hazard, self.sim) > 0
                hx, hy = hazard["position"]
                if up and not self.kraken_up[k] and \
                        math.hypot(sx - hx, sy - hy) < 9:
                    self.sound.play("splash", 0.5)
                    self.sound.play("roar", 0.35)
                self.kraken_up[k] = up

    def show_flash(self, text):
        self.flash, self.flash_until = text, self.anim_time + 2.2

    def check_game_over(self):
        reason = self.journey.game_over()
        if reason:
            self.show_over(J.GAME_OVER_TEXT[reason])
            return True
        return False

    # --- lost at sea ---------------------------------------------------------

    def get_lost(self):
        self.state = "lost"
        self.cell = J.safe_landing(self.rng, self.leg,
                                   (self.cyclone.x, self.cyclone.y))
        self.move_to = None
        self.puzzle = StarPuzzle(self.rng)
        self.star_seen = 0
        self.chart_root.show()
        self.sound.thunder()

    def update_lost(self, dt):
        j = self.journey
        j.eat(dt)
        self.sim += dt / J.step_seconds(j.resources["crew"])
        self.puzzle.update(dt)
        if self.puzzle.phase == "show":                 # a chime per star shown
            shown = len(self.puzzle.revealed())
            if shown > self.star_seen:
                self.sound.play("chime", 0.5)
            self.star_seen = shown
        else:
            self.star_seen = 0
        if self.puzzle.done:
            self.chart_root.hide()
            self.puzzle = None
            self.cyclone = Cyclone(*J.cyclone_spawn(self.rng, self.cell))
            self.state = "sail"
            self.show_flash("THE STARS GUIDE YOU BACK ON COURSE")
        self.check_game_over()

    # --- leaving an island: sail around it, then on to the next leg ----------

    def depart(self):
        isle = self.island
        node = self.island_nodes[self.leg.islands.index(isle)]
        c = self.w(*isle.center)
        radius = isle.radius * CELL
        (gx, gy), _ = self.ship_position()
        p0 = self.w(gx, gy)
        side = 1 if p0.x >= c.x else -1
        clear = radius + 1.6 * CELL
        self.depart_path = [p0,
                            Vec3(c.x + side * clear, c.y - clear * 0.3, 0),
                            Vec3(c.x + side * clear, c.y + clear * 0.4, 0),
                            Vec3(c.x + side * clear, c.y + clear * 1.1, 0)]
        self.depart_time = 0.0
        self.depart_pose = (p0, self.heading)
        # the island you landed on stays behind you
        self.behind_root.getChildren().detach()
        node.wrtReparentTo(self.behind_root)
        self.behind_cells = ((c.x, c.y), radius + 0.3 * CELL)
        self.card_root.hide()
        self.state = "depart"

    def pose_along(self, f):
        """Position and heading at fraction f (0..1) of the departure path."""
        pts = self.depart_path
        lengths = [(b - a).length() for a, b in zip(pts, pts[1:])]
        d = (f * f * (3 - 2 * f)) * sum(lengths)          # ease in and out
        for (a, b), seg in zip(zip(pts, pts[1:]), lengths):
            if d <= seg or b is pts[-1]:
                k = min(1.0, d / seg) if seg else 1.0
                pos = a + (b - a) * k
                return pos, math.degrees(math.atan2(b.y - a.y, b.x - a.x))
            d -= seg

    def update_depart(self, dt):
        self.journey.eat(dt)
        self.depart_time += dt
        f = min(1.0, self.depart_time / DEPART_SECONDS)
        pos, target = self.pose_along(f)
        _, heading = self.depart_pose
        turn = (target - heading + 180) % 360 - 180
        self.depart_pose = (pos, heading + turn * min(1.0, dt * 4))
        if self.check_game_over():
            return
        if f >= 1.0:
            self.offset = self.depart_path[-1] - to_world(*J.START)
            self.journey.next_leg()
            self.state = "sail"
            self.start_leg()

    # --- landing -------------------------------------------------------------

    def land(self, island):
        self.island = island
        self.sound.play("chime_low", 0.7)
        if island.final:
            self.show_won()
            return
        card = island.card
        self.state, self.card_phase = "card", "choose"
        self.card_title.setText(island.name)
        self.card_sub.setText(
            f"{island.episode['book']}   ·   " +
            ("A SAFE LANDING" if island.correct else "THE WRONG SHORE"))
        self.card_sub.setFg(L.GOLD if island.correct else L.DANGER)
        self.card_body.setText(card["story"])
        self.card_choices.setText(
            "\n".join(f"{k + 1}    {c['text']}"
                      for k, c in enumerate(card["choices"])))
        self.card_result.setText("")
        self.card_effects.setText("")
        self.card_footer.setText("PRESS 1 OR 2 TO CHOOSE")
        self.card_root.show()

    def choose(self, k):
        if self.state != "card" or self.card_phase != "choose":
            return
        text, effects = self.journey.resolve(self.island, k)
        self.sound.play("chime", 0.6)
        self.card_phase = "result"
        self.card_choices.setText("")
        self.card_result.setText(text)
        self.card_effects.setText(effects_text(effects))
        self.card_footer.setText("PRESS SPACE TO SET SAIL")
        reason = self.journey.game_over()
        if reason:
            self.show_over(J.GAME_OVER_TEXT[reason], before=text)

    def show_won(self):
        r, j = self.journey.resources, self.journey
        true_course = sum(1 for _, _, ok in j.history if ok)
        self.state, self.card_phase = "card", "end"
        self.ending = "won"
        self.sound.play("chime", 0.8)
        self.card_title.setText("YOU HAVE REACHED ITHACA")
        self.card_sub.setText(f"{I.ITHACA['book']}   ·   HOME")
        self.card_sub.setFg(L.GOLD)
        self.card_body.setText(I.ITHACA["story"])
        self.card_choices.setText("")
        self.card_result.setText(
            f"You came home with {r['crew']} of 12 crew and "
            f"{math.ceil(r['food'])} days of food. You held the true "
            f"course on {true_course} of {I.ROUTE_LEGS} islands.")
        self.card_effects.setText("")
        self.card_footer.setText("R: SAIL AGAIN      N: NEW VOYAGE")
        self.card_root.show()

    def show_over(self, reason, before=""):
        self.chart_root.hide()
        self.state, self.card_phase = "card", "end"
        self.ending = "over"
        self.sound.thunder()
        self.card_title.setText("THE VOYAGE ENDS")
        self.card_sub.setText(f"LEG {self.journey.leg_index + 1} OF "
                              f"{self.journey.total_legs}")
        self.card_sub.setFg(L.DANGER)
        self.card_body.setText(before)
        self.card_choices.setText("")
        self.card_result.setText(reason)
        self.card_effects.setText("")
        self.card_footer.setText("R: TRY AGAIN      N: NEW VOYAGE")
        self.card_root.show()

    # =========================================================================
    # Drawing
    # =========================================================================

    def draw(self, dt):
        t, sim = self.anim_time, self.sim
        L.animate_strokes(self.strokes, t)
        self.stars.setAlphaScale(0.85 + 0.15 * math.sin(t * 1.7))

        if self.state == "depart":
            ship_pos, heading = self.depart_pose
        else:
            (gx, gy), heading = self.ship_position()
            ship_pos = self.w(gx, gy)
        rough = (self.state == "sail" and
                 J.in_rough_water(self.rough, self.current_cell()))
        roll = 10 * math.sin(t * 6) if rough else 2.5 * math.sin(t * 0.9)
        self.ship.setPos(ship_pos + Vec3(0, 0, 0.08 * math.sin(t * 1.3)))
        self.ship.setHpr(heading, 1.2 * math.sin(t * 1.1 + 1), roll)
        rowing = (self.state == "depart" or
                  (self.state == "sail" and self.move_to is not None
                   and not self.paused))
        stroke = 28 * math.sin(t * 7) if rowing else 0
        for pivot, side in self.oars:
            pivot.setH(stroke * side)
        hurt = self.state == "sail" and sim < self.invulnerable_until
        if hurt:
            self.ship.setTransparency(TransparencyAttrib.MAlpha)
            self.ship.setAlphaScale(0.35 if math.sin(t * 20) > 0 else 1.0)
        else:
            self.ship.setAlphaScale(1.0)

        for hazard, node, tentacles, ring, height in self.krakens:
            rise = J.hazard_rise(hazard, sim)
            if rise <= 0:
                node.hide()
                continue
            node.show()
            node.setZ(-(height + 0.6) * (1 - rise))
            L.place_tentacles(tentacles, ring, height, t)

        if self.cyclone:
            self.cyclone_node.show()
            self.cyclone_node.setPos(self.w(self.cyclone.x, self.cyclone.y))
            self.cyclone_spin.setH(t * 220)
        else:
            self.cyclone_node.hide()
        for g in self.gull_nodes:
            g.setH(t * 35)
        for spin, caps in self.rough_nodes:
            L.animate_rough(spin, caps, t)
        if self.state == "title":
            self.cliff.show()
        else:
            self.cliff.hide()

        # camera: title view, or low behind the ship
        if self.state == "title":
            target_pos, target_look = TITLE_CAM
        else:
            mid = self.offset.x                # middle of this leg's sea
            p = ship_pos
            target_pos = Vec3(mid + (p.x - mid) * 0.5, p.y - 19, 12)
            target_look = Vec3(mid + (p.x - mid) * 0.7, p.y + 26, 0.0)
        k = min(1.0, dt * 2.5)
        self.cam_pos += (target_pos - self.cam_pos) * k
        self.cam_look += (target_look - self.cam_look) * k
        self.camera.setPos(self.cam_pos)
        self.camera.lookAt(self.cam_look)
        L.place_sea_tiles(self.sea_tiles, self.cam_pos.x, self.cam_pos.y)

        self.draw_hud()
        if self.state == "lost":
            self.draw_star_chart()

    # =========================================================================
    # Screens: title, HUD, island card, star chart
    # =========================================================================

    def text(self, parent, s, pos, scale, color, font, align=TextNode.ACenter,
             wrap=None, shadow=False):
        return OnscreenText(text=s, parent=parent, pos=pos, scale=scale,
                            fg=color, font=font, align=align, wordwrap=wrap,
                            mayChange=True,
                            shadow=(0, 0, 0, 0.9) if shadow else None,
                            shadowOffset=(0.012, 0.012))

    def panel(self, parent, x0, x1, z0, z1, alpha=0.9, border=True):
        fill = L.mesh("panel", [Vec3(x0, 0, z0), Vec3(x1, 0, z0),
                                Vec3(x0, 0, z1), Vec3(x1, 0, z1)],
                      [Vec4(0.05, 0.07, 0.1, alpha)] * 4,
                      [(0, 1, 2), (1, 3, 2)])
        fill.setTransparency(TransparencyAttrib.MAlpha)
        fill.setTwoSided(True)
        fill.reparentTo(parent)
        if border:
            L.lines("border", L.GOLD, 1.5, [[Vec3(x0, 0, z0), Vec3(x1, 0, z0),
                                             Vec3(x1, 0, z1), Vec3(x0, 0, z1),
                                             Vec3(x0, 0, z0)]]
                    ).reparentTo(parent)
        return fill

    def build_title(self):
        root = self.aspect2d.attachNewNode("title")
        n, rx, rz = 64, 1.12, 0.5
        verts = [Vec3(0, 0, 0.18)] + [
            Vec3(math.cos(math.tau * i / n) * rx, 0,
                 0.18 + math.sin(math.tau * i / n) * rz) for i in range(n + 1)]
        cols = ([Vec4(0.07, 0.1, 0.14, 0.55)] +
                [Vec4(0.07, 0.1, 0.14, 0.45)] * (n + 1))
        ell = L.mesh("ellipse", verts, cols,
                     [(0, i + 1, i) for i in range(1, n + 1)])
        ell.setTransparency(TransparencyAttrib.MAlpha)
        ell.setTwoSided(True)
        ell.reparentTo(root)
        self.text(root, "A VOYAGE BEYOND THE REACH OF TIME", (0, 0.57), 0.035,
                  L.MUTED, self.mono)
        self.text(root, "ODYSSEY", (0, 0.27), 0.27, L.CREAM, self.serif,
                  shadow=True)
        L.lines("rule", L.GOLD, 1.5, [[Vec3(-0.42, 0, 0.17),
                                       Vec3(0.42, 0, 0.17)]]).reparentTo(root)
        self.text(root, L.spaced("THE FRACTURED SEA"), (0, 0.03), 0.055,
                  L.CREAM, self.serif)
        self.text(root, "THE SEA REMEMBERS. TIME DOES NOT.", (0, -0.09), 0.042,
                  L.CREAM, self.serif)
        self.panel(root, -0.38, 0.38, -0.47, -0.32, alpha=0.92)
        L.lines("under", L.GOLD, 1.5, [[Vec3(-0.35, 0, -0.495),
                                        Vec3(0.35, 0, -0.495)]]
                ).reparentTo(root)
        self.text(root, L.spaced("BEGIN VOYAGE"), (0, -0.415), 0.05, L.CREAM,
                  self.serif)
        self.text(root, "PRESS ENTER OR CLICK TO SET SAIL", (0, -0.56), 0.032,
                  L.MUTED, self.mono)
        self.title_root = root

    def build_hud(self):
        root = self.aspect2d.attachNewNode("hud")
        tl, tr, bl = self.a2dTopLeft, self.a2dTopRight, self.a2dBottomLeft
        self.hud_leg = self.text(tl, "", (0.07, -0.09), 0.04, L.CREAM,
                                 self.mono, TextNode.ALeft)
        self.hud_res = [self.text(tr, "", (-0.07 - 0.33 * (3 - i), -0.09),
                                  0.04, L.CREAM, self.mono, TextNode.ARight)
                        for i in range(4)]
        self.hud_omen = self.text(root, "", (0, 0.8), 0.045, L.CREAM,
                                  self.italic, wrap=34, shadow=True)
        self.hud_prompt = self.text(root, "", (0, -0.55), 0.045, L.GOLD,
                                    self.serif, shadow=True)
        self.hud_flash = self.text(root, "", (0, 0.45), 0.055, L.DANGER,
                                   self.serif, shadow=True)
        self.hud_controls = self.text(
            bl, "ARROWS  SAIL     SPACE  PAUSE     R  RESTART     N  NEW "
                "VOYAGE", (0.07, 0.06), 0.032, L.MUTED, self.mono,
            TextNode.ALeft)
        self.hud_parts = [root, self.hud_leg, self.hud_controls] + self.hud_res

    def draw_hud(self):
        visible = self.state != "title"
        for part in self.hud_parts:
            if visible:
                part.show()
            else:
                part.hide()
        if not visible:
            return
        j, r = self.journey, self.journey.resources
        self.hud_leg.setText(f"LEG {j.leg_index + 1} OF {j.total_legs}")
        values = {"food": math.ceil(r["food"]), "health": r["health"],
                  "crew": r["crew"], "favor": r["favor"]}
        for node, key in zip(self.hud_res, ("food", "health", "crew", "favor")):
            node.setText(f"{key.upper()} {values[key]}")
            node.setFg(L.DANGER if values[key] <= LOW[key] else L.CREAM)

        self.hud_omen.setText(self.omen_text()
                              if self.state in ("sail", "lost") else "")
        if self.state == "sail" and not self.started:
            self.hud_prompt.setText("HOLD AN ARROW KEY TO SET SAIL")
        elif self.state == "sail" and self.paused:
            self.hud_prompt.setText("PAUSED")
        else:
            self.hud_prompt.setText("")
        self.hud_flash.setText(self.flash if self.anim_time < self.flash_until
                               else "")

    def omen_text(self):
        if self.omen == "final":
            return "Ithaca rises from the mist. Bring them home."
        correct = next(i for i in self.leg.islands if i.correct)
        side = "left" if correct.center[0] < J.START[0] else "right"
        if self.omen == "clear":
            return f"Athena:  \"Sail {side}, to {correct.name.title()}.\""
        if self.omen == "subtle":
            return f"Gulls circle the island {correct.episode['omen']}."
        return "The gods are silent. Poseidon stirs the sea against you."

    def build_card(self):
        root = self.aspect2d.attachNewNode("card")
        self.panel(root, -0.95, 0.95, -0.62, 0.62, alpha=0.93)
        self.card_sub = self.text(root, "", (0, 0.5), 0.034, L.GOLD, self.mono)
        self.card_title = self.text(root, "", (0, 0.36), 0.085, L.CREAM,
                                    self.serif)
        L.lines("rule", L.GOLD, 1.2, [[Vec3(-0.35, 0, 0.31),
                                       Vec3(0.35, 0, 0.31)]]).reparentTo(root)
        self.card_body = self.text(root, "", (0, 0.2), 0.048, L.CREAM,
                                   self.italic, wrap=34)
        self.card_choices = self.text(root, "", (-0.78, -0.12), 0.046,
                                      L.CREAM, self.serif, TextNode.ALeft,
                                      wrap=33)
        self.card_result = self.text(root, "", (0, -0.12), 0.048, L.CREAM,
                                     self.serif, wrap=34)
        self.card_effects = self.text(root, "", (0, -0.38), 0.038, L.GOLD,
                                      self.mono)
        self.card_footer = self.text(root, "", (0, -0.54), 0.032, L.MUTED,
                                     self.mono)
        root.hide()
        self.card_root = root

    def build_star_chart(self):
        root = self.aspect2d.attachNewNode("chart")
        self.panel(root, -1.9, 1.9, -1.1, 1.1, alpha=0.88, border=False)
        self.text(root, "LOST AT SEA", (0, 0.55), 0.08, L.CREAM, self.serif)
        self.chart_hint = self.text(root, "", (0, 0.44), 0.042, L.MUTED,
                                    self.italic)
        self.chart_stars = []
        for _ in range(7):
            s = L.box(0.045, 0.01, 0.045, L.CREAM)
            s.reparentTo(root)
            s.setR(45)
            self.chart_stars.append(s)
        self.chart_lines = None
        root.hide()
        self.chart_root = root

    def draw_star_chart(self):
        p = self.puzzle
        if p is None:
            return
        hints = {"show": "Watch the stars Odysseus steered by...",
                 "input": "Click the stars in the same order.",
                 "wrong": "The sky shifts. Watch again.",
                 "solved": "The way home is clear."}
        self.chart_hint.setText(hints[p.phase])
        shown = set(p.revealed())
        for i, (node, (x, y)) in enumerate(zip(self.chart_stars, p.stars)):
            node.setPos(x, 0, y)
            pulse = 1 + 0.15 * math.sin(self.anim_time * 4 + i)
            if p.phase == "wrong":
                node.setColorScale(1.0, 0.45, 0.4, 1)
            elif i in shown:
                node.setColorScale(1.0, 0.82, 0.5, 1)
                pulse *= 1.35
            else:
                node.setColorScale(0.6, 0.62, 0.65, 1)
            node.setScale(pulse)
        if self.chart_lines:
            self.chart_lines.removeNode()
            self.chart_lines = None
        order = list(p.revealed())
        if len(order) >= 2:
            pts = [Vec3(p.stars[i][0], 0, p.stars[i][1]) for i in order]
            self.chart_lines = L.lines("constellation", L.GOLD, 1.5, [pts])
            self.chart_lines.reparentTo(self.chart_root)


if __name__ == "__main__":
    Odyssey().run()
