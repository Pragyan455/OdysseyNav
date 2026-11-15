"""Poseidon's cyclone: drifts after the ship. If it reaches you, you're lost.

Positions are in grid cells (fractions allowed); time is in planner steps.
The ship sails 1 cell per step, the cyclone half that.
"""

import math

SPEED = 0.5            # cells per step (half the ship's speed)
HIT_RADIUS = 0.9       # cells: this close means the ship is caught


class Cyclone:
    def __init__(self, x, y):
        self.x, self.y = float(x), float(y)

    def chase(self, tx, ty, steps):
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)
        if dist < 1e-9:
            return
        move = min(dist, SPEED * steps)
        self.x += dx / dist * move
        self.y += dy / dist * move

    def hits(self, sx, sy):
        return math.hypot(sx - self.x, sy - self.y) < HIT_RADIUS
