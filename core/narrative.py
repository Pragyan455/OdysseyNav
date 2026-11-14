"""Small, deterministic story-event system for the ODYSSEY voyage."""

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryEvent:
    key: str
    text: str


EVENTS = {
    "departure": StoryEvent("departure", "The gods have abandoned these waters."),
    "approach": StoryEvent("approach", "Poseidon has awakened."),
    "waiting": StoryEvent("waiting", "Even time must yield to the sea."),
    "escape": StoryEvent("escape", "The passage is open."),
    "arrival": StoryEvent("arrival", "After all this time, home."),
}


class NarrativeEngine:
    """Emit story beats once, based on navigation state and storm proximity."""

    def __init__(self, approach_radius=5, escape_radius=7):
        if escape_radius <= approach_radius:
            raise ValueError("escape_radius must exceed approach_radius")
        self.approach_radius = approach_radius
        self.escape_radius = escape_radius
        self.reset()

    def reset(self):
        self.seen = set()
        self.current = None
        self.encountered_storm = False

    def _emit(self, key):
        if key in self.seen:
            return None
        self.seen.add(key)
        self.current = EVENTS[key]
        return self.current

    def update(self, status, distance_to_storm=None, storm_active=False):
        """Return a new StoryEvent, or None when no new beat occurs.

        distance_to_storm is in grid cells; None means unavailable.
        """
        if status == "ARRIVED":
            return self._emit("arrival")
        if status in ("PAUSED", "NO ROUTE"):
            return None

        if "departure" not in self.seen:
            return self._emit("departure")

        near = (distance_to_storm is not None
                and distance_to_storm <= self.approach_radius)
        escaped = (distance_to_storm is not None
                   and distance_to_storm >= self.escape_radius)

        if near and storm_active:
            self.encountered_storm = True
            if "approach" not in self.seen:
                return self._emit("approach")

        if status == "WAITING" and self.encountered_storm:
            return self._emit("waiting")

        if self.encountered_storm and (escaped or not storm_active):
            return self._emit("escape")

        return None
