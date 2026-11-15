"""Star navigation: the puzzle you solve to find your way after the cyclone.

A few stars light up one by one; then you click them in the same order.
A wrong click shifts the sky (a fresh pattern). Times are in real seconds.
Star positions are in screen units: x in about [-0.85, 0.85], y in
[-0.4, 0.3] (centered, y up).
"""

import math

NUM_STARS = 7
PATTERN_LENGTH = 4
SHOW_SECONDS = 0.7      # each star of the pattern lights for this long
PAUSE_SECONDS = 0.4     # after the pattern, before you can click
WRONG_SECONDS = 1.0     # red flash before the sky shifts
SOLVED_SECONDS = 0.9    # "homeward bound" before you sail again
CLICK_RADIUS = 0.07
MIN_GAP = 0.22


class StarPuzzle:
    def __init__(self, rng, num_stars=NUM_STARS, length=PATTERN_LENGTH):
        self.rng = rng
        self.num_stars = num_stars
        self.length = length
        self.new_pattern()

    def new_pattern(self):
        stars = []
        while len(stars) < self.num_stars:
            p = (self.rng.uniform(-0.85, 0.85), self.rng.uniform(-0.4, 0.3))
            if all(math.hypot(p[0] - q[0], p[1] - q[1]) >= MIN_GAP
                   for q in stars):
                stars.append(p)
        self.stars = stars
        self.order = self.rng.sample(range(self.num_stars), self.length)
        self.clicked = []
        self.phase = "show"           # show -> input -> (wrong | solved)
        self.timer = 0.0

    # --- time -----------------------------------------------------------------

    def update(self, dt):
        self.timer += dt
        if (self.phase == "show" and
                self.timer >= SHOW_SECONDS * self.length + PAUSE_SECONDS):
            self.phase, self.timer = "input", 0.0
        elif self.phase == "wrong" and self.timer >= WRONG_SECONDS:
            self.new_pattern()

    @property
    def done(self):
        return self.phase == "solved" and self.timer >= SOLVED_SECONDS

    def revealed(self):
        """Stars of the pattern visible right now, in order."""
        if self.phase == "show":
            n = min(self.length, int(self.timer / SHOW_SECONDS) + 1)
            return self.order[:n]
        if self.phase == "solved":
            return self.order
        return self.clicked

    # --- clicks ---------------------------------------------------------------

    def star_at(self, x, y):
        best, best_d = None, CLICK_RADIUS
        for i, (sx, sy) in enumerate(self.stars):
            d = math.hypot(x - sx, y - sy)
            if d <= best_d:
                best, best_d = i, d
        return best

    def click(self, x, y):
        """Returns 'ok', 'wrong', 'solved', or None (ignored)."""
        if self.phase != "input":
            return None
        i = self.star_at(x, y)
        if i is None or i in self.clicked:
            return None
        if i != self.order[len(self.clicked)]:
            self.phase, self.timer = "wrong", 0.0
            return "wrong"
        self.clicked.append(i)
        if len(self.clicked) == self.length:
            self.phase, self.timer = "solved", 0.0
            return "solved"
        return "ok"
