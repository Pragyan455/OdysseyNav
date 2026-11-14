"""Random voyages for the manual (arrow-key) mode.

Each seed gives one map: random islands plus several krakens placed on the
way to Ithaca. The Chronos planner checks every map: it must have a safe
route, and the length of that route is the "CHRONOS TIME" to beat.
"""

import math
import random

from core import scenario

NUM_ISLANDS = 8
NUM_KRAKENS = 3
ISLAND_RADIUS_PX = (30, 85)
CHANNEL_PX = 25              # keep at least one cell of water between islands
HARBOR_PX = 60               # keep water around the start and Ithaca


class Voyage:
    def __init__(self, seed, islands, obstacles, hazards, path):
        self.seed = seed
        self.islands = islands        # [(px, py, radius_px), ...]
        self.obstacles = obstacles    # blocked grid cells
        self.hazards = hazards        # ChronosPlanner hazard dicts
        self.path = path              # the planner's best route

    @property
    def chronos_steps(self):
        return len(self.path) - 1


def island_cells(islands):
    """A cell is blocked if its center is inside an island."""
    blocked = set()
    for gx in range(scenario.GRID_WIDTH):
        for gy in range(scenario.GRID_HEIGHT):
            px, py = scenario.grid_to_pixel(gx, gy)
            if any(math.hypot(px - ix, py - iy) < r for ix, iy, r in islands):
                blocked.add((gx, gy))
    return blocked


def _random_islands(rng):
    start = scenario.grid_to_pixel(*scenario.START)
    goal = scenario.grid_to_pixel(*scenario.GOAL)
    islands = []
    tries = 0
    while len(islands) < NUM_ISLANDS and tries < 500:
        tries += 1
        r = rng.uniform(*ISLAND_RADIUS_PX)
        x = rng.uniform(230, 950)
        y = rng.uniform(40 + r * 0.5, scenario.HEIGHT - 40 - r * 0.5)
        if math.hypot(x - start[0], y - start[1]) < r + HARBOR_PX:
            continue
        if math.hypot(x - goal[0], y - goal[1]) < r + HARBOR_PX:
            continue
        if any(math.hypot(x - ix, y - iy) < r + ir + CHANNEL_PX
               for ix, iy, ir in islands):
            continue
        islands.append((round(x), round(y), round(r)))
    return islands


def _random_krakens(rng, route):
    """Put krakens on the open-water route so they are actually in the way."""
    hazards = []
    for k in range(NUM_KRAKENS):
        f = (k + 1) / (NUM_KRAKENS + 1) + rng.uniform(-0.08, 0.08)
        x, y, _ = route[int(f * (len(route) - 1))]
        period = rng.randint(8, 14)
        hazards.append({
            "position": (x, y),
            "radius": rng.choice((0, 1)),
            "period": period,
            "active_duration": max(3, round(period * rng.uniform(0.4, 0.65))),
        })
    return hazards


def generate(seed, planner_cls):
    """Build a solvable random voyage. Same seed -> same map."""
    rng = random.Random(seed)
    for _ in range(200):
        islands = _random_islands(rng)
        obstacles = island_cells(islands)
        if scenario.START in obstacles or scenario.GOAL in obstacles:
            continue
        planner = planner_cls(scenario.GRID_WIDTH, scenario.GRID_HEIGHT,
                              obstacles)
        open_route = planner.plan(scenario.START, scenario.GOAL, hazards=[],
                                  start_time=0, max_time=scenario.MAX_TIME)
        if not open_route:
            continue
        hazards = _random_krakens(rng, open_route)
        path = planner.plan(scenario.START, scenario.GOAL, hazards=hazards,
                            start_time=0, max_time=scenario.MAX_TIME)
        if path:
            return Voyage(seed, islands, obstacles, hazards, path)
    raise RuntimeError(f"no solvable voyage for seed {seed}")


def hazard_hits(hazards, cell, sim_steps):
    """Is a kraken more than halfway up over this cell right now?

    Matches the planner: a ship that follows a planned route is never hit,
    because it leaves a cell before a kraken there is half risen and enters
    a cell only after the kraken there is half sunk.
    """
    for hazard in hazards:
        hx, hy = hazard["position"]
        if math.hypot(cell[0] - hx, cell[1] - hy) <= hazard["radius"]:
            if scenario.hazard_rise(hazard, sim_steps) > 0.5:
                return True
    return False
