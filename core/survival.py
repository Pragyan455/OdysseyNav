"""Ship survival rules independent of Pygame rendering."""
import math


class ShipSurvival:
    def __init__(self, max_hull=100, repairs=3, damage_per_hit=18, hit_interval=1.5, repair_amount=30):
        self.max_hull = int(max_hull)
        self.hull = self.max_hull
        self.repairs = int(repairs)
        self.damage_per_hit = int(damage_per_hit)
        self.hit_interval = float(hit_interval)
        self.repair_amount = int(repair_amount)
        self.last_hit_time = float('-inf')
        self.hits = 0

    @property
    def sunk(self):
        return self.hull <= 0

    def repair(self):
        if self.sunk or self.repairs <= 0 or self.hull >= self.max_hull:
            return False
        self.repairs -= 1
        self.hull = min(self.max_hull, self.hull + self.repair_amount)
        return True

    def update(self, x, y, t, hazards):
        """Apply one hit when inside an active storm and cooldown elapsed.

        Coordinates are grid-space floats. Returns True only on a new hit.
        """
        if self.sunk or t - self.last_hit_time < self.hit_interval:
            return False
        for hazard in hazards:
            period = hazard['period']
            if period <= 0 or t % period >= hazard['active_duration']:
                continue
            hx, hy = hazard['position']
            if math.hypot(x - hx, y - hy) <= hazard['radius'] + 0.55:
                self.hull = max(0, self.hull - self.damage_per_hit)
                self.last_hit_time = float(t)
                self.hits += 1
                return True
        return False
