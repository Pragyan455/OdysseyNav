"""The voyage home: resources, legs, omens and island events.

Pure game rules, no drawing. main3d.py shows them in 3D.

A journey is 8 legs (one per Odyssey episode) and a final leg to Ithaca.
Each leg is a small sea on a grid: the ship starts at the bottom, and one or
two islands wait at the far end. The Chronos planner checks that every
island can be reached past the krakens. Time on a leg is counted in planner
steps (one step = the ship sailing one cell).
"""

import math
import random
from collections import deque

from core import islands
from core.chronos import ChronosPlanner

# --- the sea of one leg ---------------------------------------------------------
WIDTH, LENGTH = 23, 40            # grid cells
START = (11, 2)
ISLAND_RADIUS = 3.4               # cells: island cells are blocked
HARBOR_REACH = 1.3                # cells past the shore that count as landing
MAX_PLAN_STEPS = 200

# --- resources -----------------------------------------------------------------
START_RESOURCES = {"food": 30.0, "health": 10, "crew": 12, "favor": 6}
MAX_RESOURCES = {"food": 40.0, "health": 10, "crew": 12, "favor": 10}
FOOD_PER_SECOND = 0.3             # eaten every second at sea
KRAKEN_DAMAGE = {"health": -3, "crew": -1}
INVULNERABLE_STEPS = 4            # after a kraken hit
CLEAR_OMEN_FAVOR = 7              # favor >= this: Athena shows the way
CYCLONE_FAVOR = 3                 # favor <= this: vague omen, cyclone hunts
ROUGH_CELLS_PER_DAMAGE = 2        # rough water: -1 health per 2 cells sailed

BASE_STEP_SECONDS = 0.32          # seconds per cell with a full crew

GAME_OVER_TEXT = {
    "food": "The last of the food is gone. The crew starves on the open sea.",
    "health": "Odysseus falls. The voyage ends far from home.",
    "crew": "No one is left to row. The ship drifts forever.",
    "favor": "The gods turn away. Poseidon drags the ship beneath the waves.",
}


def step_seconds(crew):
    """Fewer crew row slower."""
    crew = max(crew, 0)
    return BASE_STEP_SECONDS / (0.45 + 0.55 * crew / MAX_RESOURCES["crew"])


def omen_level(favor):
    if favor >= CLEAR_OMEN_FAVOR:
        return "clear"
    if favor <= CYCLONE_FAVOR:
        return "vague"
    return "subtle"


# --- krakens (same timing rule as the planner) ---------------------------------

def hazard_active(hazard, step):
    return step % hazard["period"] < hazard["active_duration"]


def hazard_rise(hazard, steps):
    """0.0 (hidden) .. 1.0 (fully up). The picture during (t, t+1] shows the
    planner's state at t+1; it rises during the step before it turns on and
    sinks during the step after it turns off."""
    shown = math.ceil(steps - 1e-9)
    frac = min(1.0, max(0.0, steps - (shown - 1)))
    now, before = hazard_active(hazard, shown), hazard_active(hazard, shown - 1)
    if now and not before:
        return frac
    if now:
        return 1.0
    if before:
        return 1.0 - frac
    return 0.0


def hazard_hits(hazards, cell, steps):
    """A kraken more than halfway up over this cell. A ship following a
    planned route is never hit: it leaves before one is half risen and
    enters only after one is half sunk."""
    for h in hazards:
        hx, hy = h["position"]
        if math.hypot(cell[0] - hx, cell[1] - hy) <= h["radius"]:
            if hazard_rise(h, steps) > 0.5:
                return True
    return False


# --- islands and legs ----------------------------------------------------------

class Island:
    def __init__(self, center, episode, correct, harsh, final=False):
        self.center = center          # (gx, gy), may be fractional
        self.episode = episode        # entry from islands.EPISODES / ITHACA
        self.correct = correct
        self.harsh = harsh
        self.final = final
        self.radius = ISLAND_RADIUS

    @property
    def name(self):
        return self.episode["name"]

    def covers(self, cell):
        return math.hypot(cell[0] - self.center[0],
                          cell[1] - self.center[1]) < self.radius

    def in_harbor(self, cell):
        d = math.hypot(cell[0] - self.center[0], cell[1] - self.center[1])
        return self.radius <= d < self.radius + HARBOR_REACH

    @property
    def card(self):
        if self.final:
            return None
        return self.episode["harsh" if self.harsh else "calm"]


class Leg:
    def __init__(self, index, islands_, reefs, obstacles, hazards, routes):
        self.index = index
        self.islands = islands_
        self.reefs = reefs            # [(gx, gy, radius)] small rocks
        self.obstacles = obstacles    # blocked cells (islands + reefs)
        self.hazards = hazards        # krakens, ChronosPlanner format
        self.routes = routes          # planner route to each island

    @property
    def final(self):
        return self.islands[0].final

    def landed(self, cell):
        """The island whose harbor this cell is in, or None."""
        for island in self.islands:
            if cell not in self.obstacles and island.in_harbor(cell):
                return island
        return None

    def open(self, cell):
        x, y = cell
        return 0 <= x < WIDTH and 0 <= y < LENGTH and cell not in self.obstacles


def _cells_within(circles):
    return {(x, y) for x in range(WIDTH) for y in range(LENGTH)
            if any(math.hypot(x - cx, y - cy) < r for cx, cy, r in circles)}


def _harbor_target(island, obstacles):
    """The landing cell nearest the start, for the planner."""
    cells = [(x, y) for x in range(WIDTH) for y in range(LENGTH)
             if (x, y) not in obstacles and island.in_harbor((x, y))]
    return min(cells, key=lambda c: (c[1], abs(c[0] - START[0])))


def generate_leg(index, seed):
    """Leg `index` (0-based) of the journey with this seed.
    Legs 0..7 have two islands; leg 8 is Ithaca alone."""
    rng = random.Random(seed * 1000 + index)
    final = index >= islands.ROUTE_LEGS
    for _ in range(300):
        if final:
            isles = [Island((11.0, 33.5), islands.ITHACA, True, False,
                            final=True)]
        else:
            correct = islands.EPISODES[index]
            wrong = rng.choice([e for e in islands.EPISODES
                                if e is not correct])
            left = (rng.uniform(4.0, 6.0), rng.uniform(31.0, 34.0))
            right = (rng.uniform(16.0, 18.0), rng.uniform(31.0, 34.0))
            if rng.random() < 0.5:
                left, right = right, left
            isles = [Island(left, correct, True, False),
                     Island(right, wrong, False, True)]

        reefs = []
        while len(reefs) < 6:
            r = (rng.uniform(4, 25), rng.uniform(1, WIDTH - 2))
            reef = (r[1], r[0], rng.uniform(0.7, 1.2))
            if math.hypot(reef[0] - START[0], reef[1] - START[1]) > 4:
                reefs.append(reef)
        obstacles = _cells_within(
            reefs + [(i.center[0], i.center[1], i.radius) for i in isles])
        if START in obstacles:
            continue

        planner = ChronosPlanner(WIDTH, LENGTH, obstacles)
        targets = [_harbor_target(i, obstacles) for i in isles]
        open_routes = [planner.plan(START, t, hazards=[], start_time=0,
                                    max_time=MAX_PLAN_STEPS) for t in targets]
        if not all(open_routes):
            continue

        hazards = []
        for k in range(2 if final else 3):
            route = open_routes[k % len(open_routes)]
            x, y, _ = route[int(rng.uniform(0.3, 0.75) * (len(route) - 1))]
            if math.hypot(x - START[0], y - START[1]) < 4:
                continue
            period = rng.randint(8, 14)
            hazards.append({
                "position": (x, y),
                "radius": rng.choice((0, 1)),
                "period": period,
                "active_duration": max(3, round(period *
                                                rng.uniform(0.4, 0.65))),
            })
        routes = [planner.plan(START, t, hazards=hazards, start_time=0,
                               max_time=MAX_PLAN_STEPS) for t in targets]
        if all(routes):
            return Leg(index, isles, reefs, obstacles, hazards, routes)
    raise RuntimeError(f"could not build leg {index} for seed {seed}")


# --- rough water: appears as the gods' favor drops ------------------------------

def rough_water_count(favor):
    if favor >= CLEAR_OMEN_FAVOR:
        return 0
    if favor <= CYCLONE_FAVOR:
        return 4
    return 2


def rough_water(leg, favor, rng):
    """Churning patches [(gx, gy, radius)] on the way to the islands.
    They never block; sailing through them costs health."""
    patches = []
    routes = leg.routes
    for k in range(rough_water_count(favor) * 6):
        if len(patches) == rough_water_count(favor):
            break
        route = routes[k % len(routes)]
        x, y, _ = route[int(rng.uniform(0.2, 0.85) * (len(route) - 1))]
        r = rng.uniform(1.6, 2.4)
        far_from_start = math.hypot(x - START[0], y - START[1]) > r + 3
        clear_of_shore = all(math.hypot(x - i.center[0], y - i.center[1])
                             > i.radius + HARBOR_REACH + r
                             for i in leg.islands)
        apart = all(math.hypot(x - px, y - py) > r + pr + 1
                    for px, py, pr in patches)
        if far_from_start and clear_of_shore and apart:
            patches.append((x + rng.uniform(-0.5, 0.5), y, r))
    return patches


def in_rough_water(patches, cell):
    return any(math.hypot(cell[0] - x, cell[1] - y) < r for x, y, r in patches)


# --- where the cyclone appears, and where it throws you -------------------------

def cyclone_spawn(rng, ship_xy, min_dist=14):
    edge = ([(x, LENGTH - 1) for x in range(WIDTH)] +
            [(0, y) for y in range(LENGTH)] +
            [(WIDTH - 1, y) for y in range(LENGTH)])
    far = [c for c in edge
           if math.hypot(c[0] - ship_xy[0], c[1] - ship_xy[1]) >= min_dist]
    return rng.choice(far or edge)


def reachable_water(leg):
    """Every open cell from which some island's harbor can be reached."""
    start = [(x, y) for x in range(WIDTH) for y in range(LENGTH)
             if leg.landed((x, y))]
    seen, queue = set(start), deque(start)
    while queue:
        x, y = queue.popleft()
        for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if n not in seen and leg.open(n):
                seen.add(n)
                queue.append(n)
    return seen


def safe_landing(rng, leg, cyclone_xy, min_dist=8):
    """Where the cyclone throws the ship: open water that can still reach an
    island, away from the cyclone, not under a kraken, not already ashore."""
    def near_kraken(c):
        return any(math.hypot(c[0] - h["position"][0],
                              c[1] - h["position"][1]) <= h["radius"] + 1
                   for h in leg.hazards)

    options = sorted(
        c for c in reachable_water(leg)
        if not leg.landed(c) and not near_kraken(c) and 2 <= c[1] <= LENGTH - 8
        and math.hypot(c[0] - cyclone_xy[0], c[1] - cyclone_xy[1]) >= min_dist)
    return rng.choice(options) if options else START


# --- the journey ---------------------------------------------------------------

class Journey:
    def __init__(self, seed):
        self.seed = seed
        self.rng = random.Random(seed)
        self.resources = dict(START_RESOURCES)
        self.leg_index = 0
        self.history = []             # (leg, island name, correct)

    @property
    def total_legs(self):
        return islands.ROUTE_LEGS + 1

    def leg(self):
        return generate_leg(self.leg_index, self.seed)

    def apply(self, effects):
        for key, delta in effects.items():
            value = self.resources[key] + delta
            self.resources[key] = max(0, min(MAX_RESOURCES[key], value))

    def eat(self, seconds):
        self.apply({"food": -FOOD_PER_SECOND * seconds})

    def game_over(self):
        """The reason the voyage ended, or None."""
        for key in ("food", "health", "crew", "favor"):
            if self.resources[key] <= 0:
                return key
        return None

    def resolve(self, island, choice_index):
        """Play a choice on an island card. Returns (result text, effects)."""
        choice = island.card["choices"][choice_index]
        if "chance" in choice:
            won = self.rng.random() < choice["chance"]
            effects = choice["win"] if won else choice["lose"]
            text = choice["win_result"] if won else choice["lose_result"]
        else:
            effects, text = choice["effects"], choice["result"]
        self.apply(effects)
        self.history.append((self.leg_index, island.name, island.correct))
        return text, effects

    def next_leg(self):
        self.leg_index += 1
