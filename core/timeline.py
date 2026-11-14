"""Deterministic, read-only replay of a planned ODYSSEY voyage."""
from dataclasses import dataclass


@dataclass(frozen=True)
class TimelineFrame:
    time: float
    position: tuple[float, float]
    storm_active: bool
    waiting: bool
    arrived: bool


class VoyageTimeline:
    def __init__(self, path, hazards=None):
        self.path = list(path or [])
        self.hazards = list(hazards or [])
        self.start = float(self.path[0][2]) if self.path else 0.0
        self.end = float(self.path[-1][2]) if self.path else 0.0
        self.wait_times = [float(a[2]) for a, b in zip(self.path, self.path[1:])
                           if a[:2] == b[:2]]

    def frame(self, time):
        if not self.path:
            return None
        t = max(self.start, min(float(time), self.end))
        position = tuple(map(float, self.path[-1][:2]))
        waiting = False
        for a, b in zip(self.path, self.path[1:]):
            if t < b[2]:
                fraction = (t - a[2]) / (b[2] - a[2]) if b[2] != a[2] else 0.0
                position = (a[0] + (b[0] - a[0]) * fraction,
                            a[1] + (b[1] - a[1]) * fraction)
                waiting = a[:2] == b[:2]
                break
        storm_active = any(
            h['period'] > 0 and t % h['period'] < h['active_duration']
            for h in self.hazards
        )
        return TimelineFrame(t, position, storm_active, waiting, t >= self.end)

    def clamp(self, time):
        return max(self.start, min(float(time), self.end))
