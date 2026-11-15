"""Easter eggs from the Odyssey, hidden in the title scene.

  The Cyclops' eye (Book IX)   a shut slit in the cliff; click it and it
                               opens: "Who is blinding you?" "Nobody!"
  Argos (Book XVII)            the old hound on the shore; click him and he
                               wags his tail: twenty years, and he knows you
  Penelope's loom (Book II)    click it and the shroud unravels, then she
                               weaves it again
  The twelve axes (Book XXI)   click an axe or type ITHACA: the bow sings, an
                               arrow flies through all twelve, and your sail
                               turns gold for the voyage
"""

import math

from panda3d.core import NodePath, Point2, Point3, TextNode, Vec3

import look3d as L

EYE_POS = Point3(52.5, 109.6, 10.0)
ARGOS_POS = Point3(-5.0, -7.6, 0.85)
LOOM_POS = Point3(-4.9, 2.0, -0.2)
AXES_Y, AXES_Z = -8.0, 0.0
AXE_XS = [-2.6 + k * 0.47 for k in range(12)]
AXE_SIZE = 0.55
MESSAGE_SECONDS = 6.0

MESSAGES = {
    "eye": "“Who is blinding you, Polyphemus?” — “Nobody!”"
           "\n(Book IX)",
    "argos": "Argos knew him at once. After twenty years, the old hound "
             "lifted his head and wagged his tail.\n(Book XVII)",
    "loom": "By day Penelope wove the shroud; by night she unravelled it, "
            "and kept the suitors waiting three years.\n(Book II)",
    "axes": "Through all twelve axes! The gods mark you: your sail is "
            "golden for this voyage.\n(Book XXI)",
}


class Eggs:
    def __init__(self, app):
        self.app = app
        self.root = app.render.attachNewNode("easter-eggs")
        self.timers = {}                 # egg -> seconds since it was found
        self.found = set()
        self.typed = ""
        self.build_eye()
        self.build_argos()
        self.build_loom()
        self.build_axes()
        self.message = app.text(app.aspect2d, "", (0, 0.8), 0.036,
                                L.GOLD, app.italic, wrap=44, shadow=True)
        self.message_until = 0.0
        app.buttonThrowers[0].node().setKeystrokeEvent("keystroke")
        app.accept("keystroke", self.on_key)

    # --- props -----------------------------------------------------------------

    def build_eye(self):
        self.eye = self.root.attachNewNode("cyclops-eye")
        self.eye.setPos(EYE_POS)
        shut = [Vec3(math.cos(a) * 2.2, 0, math.sin(a) * 0.18 *
                     (1 if a < math.pi else -1))
                for a in [i / 24 * math.tau for i in range(25)]]
        self.eye_shut = L.lines("eye-shut", L.GOLD, 3, [shut])
        self.eye_shut.reparentTo(self.eye)
        self.eye_open = self.eye.attachNewNode("eye-open")
        white = L.disc(1.0, L.rgb(255, 200, 120), n=24)
        white.reparentTo(self.eye_open)
        white.setScale(2.2, 1, 0.9)
        iris = L.disc(0.62, L.rgb(210, 70, 26), n=18)
        iris.reparentTo(self.eye_open)
        iris.setY(-0.02)
        pupil = L.disc(0.3, L.rgb(12, 4, 4), n=14)
        pupil.reparentTo(self.eye_open)
        pupil.setY(-0.04)
        pupil.setScale(0.6, 1, 1.2)
        for node in (self.eye_shut, self.eye_open):
            node.setLightOff()
            node.setFogOff()
        self.eye_open.hide()

    def build_argos(self):
        dog = self.root.attachNewNode("argos")
        dog.setPos(ARGOS_POS)
        dog.setH(-65)
        coat, muzzle = L.rgb(84, 62, 44), L.rgb(120, 92, 64)

        def part(sx, sy, sz, color, pos, hpr=(0, 0, 0), parent=dog):
            b = L.box(sx, sy, sz, color)
            b.reparentTo(parent)
            b.setPos(*pos)
            b.setHpr(*hpr)
            return b

        part(1.4, 0.55, 0.42, coat, (0, 0, 0.24))               # lying body
        part(0.5, 0.5, 0.5, coat, (0.62, 0, 0.36))              # chest
        part(0.5, 0.36, 0.36, coat, (0.92, 0, 0.66), (0, 0, -8))  # head up
        part(0.34, 0.24, 0.22, muzzle, (1.24, 0, 0.6), (0, 0, -8))
        for y in (-0.14, 0.14):
            part(0.12, 0.08, 0.26, coat, (0.84, y, 0.9), (0, 0, 20))  # ears
            part(0.7, 0.13, 0.12, coat, (1.0, y * 1.4, 0.06))     # paws out
            part(0.4, 0.16, 0.2, coat, (-0.5, y * 2.2, 0.1))       # hind legs
        self.tail = dog.attachNewNode("tail")
        self.tail.setPos(-0.7, 0, 0.32)
        part(0.6, 0.09, 0.09, coat, (-0.28, 0, 0.05), (0, 0, -15),
             parent=self.tail)
        dog.setScale(1.25)
        self.argos = dog

    def build_loom(self):
        loom = self.root.attachNewNode("loom")
        loom.setPos(LOOM_POS)
        loom.setH(20)
        loom.setScale(0.62)
        rock = L.reef(1.6, seed=31)
        rock.reparentTo(loom)
        rock.setScale(1.4, 1.0, 0.45)
        wood = L.rgb(96, 66, 42)
        frame = loom.attachNewNode("frame")
        frame.setZ(0.55)
        for x in (-0.85, 0.85):
            post = L.box(0.13, 0.13, 2.3, wood)
            post.reparentTo(frame)
            post.setPos(x, 0, 1.15)
            post.setR(-4 if x < 0 else 4)
        for z in (2.25, 1.75):
            beam = L.box(1.95, 0.14, 0.14, wood)
            beam.reparentTo(frame)
            beam.setPos(0, 0, z)
        warp = [[Vec3(-0.72 + k * 0.11, -0.02, 1.7), Vec3(-0.72 + k * 0.11,
                                                         -0.02, 0.4)]
                for k in range(14)]
        L.lines("warp", L.GOLD, 1.2, warp).reparentTo(frame)
        for k in range(14):
            weight = L.sphere(0.06, L.rgb(150, 110, 70), seed=k)
            weight.reparentTo(frame)
            weight.setPos(-0.72 + k * 0.11, -0.02, 0.36)
        self.cloth = []
        for r in range(9):                           # the shroud, row by row
            row = L.box(1.5, 0.05, 0.1, L.CRIMSON if r % 2 else
                        L.CRIMSON_DARK)
            row.reparentTo(frame)
            row.setPos(0, -0.03, 1.62 - r * 0.11)
            self.cloth.append(row)
        self.loom = loom

    def build_axes(self):
        self.axes = []
        for k, x in enumerate(AXE_XS):
            axe = self.root.attachNewNode("axe")
            axe.setPos(x, AXES_Y, AXES_Z)
            axe.setScale(AXE_SIZE)
            handle = L.box(0.07, 0.07, 1.1, L.rgb(96, 66, 42))
            handle.reparentTo(axe)
            handle.setZ(0.45)
            head = L.box(0.07, 0.5, 0.36, L.BRONZE)
            head.reparentTo(axe)
            head.setZ(1.05)
            ring = L.disc(0.07, L.rgb(10, 6, 6), n=10, axis="x")
            ring.reparentTo(head)
            ring.setX(-0.04)
            self.axes.append(axe)
        self.arrow = L.lines("arrow", L.GOLD_BRIGHT, 3,
                             [[Vec3(-0.9, 0, 0), Vec3(0.9, 0, 0)],
                              [Vec3(0.9, 0, 0), Vec3(0.7, 0, 0.12)],
                              [Vec3(0.9, 0, 0), Vec3(0.7, 0, -0.12)],
                              [Vec3(-0.9, 0, 0), Vec3(-1.1, 0, 0.14)],
                              [Vec3(-0.9, 0, 0), Vec3(-1.1, 0, -0.14)]])
        self.arrow.reparentTo(self.root)
        self.arrow.setScale(AXE_SIZE)
        self.arrow.setFogOff()
        self.arrow.hide()

    # --- finding them ----------------------------------------------------------

    def screen_pos(self, point):
        """A world point -> render2d coordinates, or None if off-screen."""
        app = self.app
        rel = app.cam.getRelativePoint(app.render, point)
        p2 = Point2()
        if app.camLens.project(rel, p2):
            return p2
        return None

    def hit(self, mx, my):
        """Which egg is under the mouse (render2d coordinates), if any."""
        aspect = self.app.getAspectRatio()
        spots = [("eye", EYE_POS, 0.07), ("argos", ARGOS_POS + Vec3(0, 0, 0.4),
                                          0.09),
                 ("loom", LOOM_POS + Vec3(0, 0, 1.6), 0.11)]
        spots += [("axes", Point3(x, AXES_Y, AXES_Z + 0.9 * AXE_SIZE), 0.03)
                  for x in AXE_XS]
        for name, point, radius in spots:
            p = self.screen_pos(point)
            if p and math.hypot((mx - p.x) * aspect, my - p.y) < radius:
                return name
        return None

    def click(self, mx, my):
        egg = self.hit(mx, my)
        if egg:
            self.trigger(egg)
        return egg

    def on_key(self, key):
        if self.app.state != "title" or not key.isalpha():
            return
        self.typed = (self.typed + key.lower())[-6:]
        if self.typed == "ithaca":
            self.trigger("axes")

    def trigger(self, egg):
        app = self.app
        self.timers[egg] = 0.0
        self.found.add(egg)
        self.message.setText(MESSAGES[egg])
        self.message_until = app.anim_time + MESSAGE_SECONDS
        sound = {"eye": ("roar", 0.35), "argos": ("chime_low", 0.6),
                 "loom": ("chime", 0.45), "axes": ("bow", 1.0)}[egg]
        app.sound.play(*sound)
        if egg == "axes":
            app.grant_golden_sail()

    # --- every frame -------------------------------------------------------------

    def update(self, dt):
        title = self.app.state == "title"
        if title:
            self.root.show()
        else:
            self.root.hide()
            self.message.setText("")
            return
        for egg in list(self.timers):
            self.timers[egg] += dt
        t = self.timers
        eye_open = "eye" in t and t["eye"] < 4.0     # the eye opens, then shuts
        self.eye_open.show() if eye_open else self.eye_open.hide()
        self.eye_shut.hide() if eye_open else self.eye_shut.show()
        if "argos" in t and t["argos"] < 3.0:        # he wags his tail
            self.tail.setH(35 * math.sin(t["argos"] * 18))
            self.tail.setR(-25)
        else:
            self.tail.setH(0)
            self.tail.setR(0)
        rows = len(self.cloth)                       # the shroud unravels...
        if "loom" in t:
            k = t["loom"]
            shown = rows - int(min(rows, k * 6)) if k < 2.0 else \
                min(rows, int((k - 2.0) * 3))        # ...and is woven again
            for r, row in enumerate(self.cloth):
                row.show() if r < shown else row.hide()
        if "axes" in t and t["axes"] < 1.4:          # the arrow's flight
            f = min(1.0, t["axes"] / 0.9)
            x = AXE_XS[0] - 1.5 + (AXE_XS[-1] - AXE_XS[0] + 3) * f
            self.arrow.show()
            self.arrow.setPos(x, AXES_Y - 0.03, AXES_Z + 1.05 * AXE_SIZE)
        else:
            self.arrow.hide()
        if self.app.anim_time > self.message_until:
            self.message.setText("")
