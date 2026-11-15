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
from core.encounters import ENCOUNTERS, EncounterEngine      # teammate's
from core.strategy import StrategyPlanner                    # teammate's
from core.survival import ShipSurvival                       # teammate's

# --- the sea of one leg ---------------------------------------------------------
WIDTH, LENGTH = 23, 40            # grid cells
START = (11, 2)
ISLAND_RADIUS = 3.4               # cells: island cells are blocked
HARBOR_REACH = 1.3                # cells past the shore that count as landing
MAX_PLAN_STEPS = 200

# --- resources -----------------------------------------------------------------
_SHIP = ShipSurvival()             # hull numbers from the 2D game's rules
START_RESOURCES = {"food": 30.0, "health": 10, "crew": 12, "favor": 0,
                   "hull": _SHIP.max_hull, "wood": 1, "rope": 0,
                   "medicine": 0}
MAX_RESOURCES = {"food": 40.0, "health": 10, "crew": 12, "favor": 20,
                 "hull": _SHIP.max_hull, "wood": 9, "rope": 9, "medicine": 5}
FOOD_PER_SECOND = 0.3             # eaten every second at sea
KRAKEN_DAMAGE = {"hull": -_SHIP.damage_per_hit, "crew": -1}
ROUGH_DAMAGE = {"hull": -6}
REPAIR_COST = {"wood": -2, "rope": -1}       # same as the 2D game's repair
REPAIR_HULL = _SHIP.repair_amount
HEAL_COST, HEAL_HEALTH = {"medicine": -1}, 3
RATION_FOOD = 2.0                 # one 2D-game ration = 2 days of food here
LOOT = {"wood": (1, 3), "rope": (0, 2), "medicine": (0, 1)}  # per landing
INVULNERABLE_STEPS = 4            # after a kraken hit
CLEAR_OMEN_FAVOR = 8              # favor >= this: Athena shows the way
CYCLONE_FAVOR = 3                 # favor <= this: vague omen, cyclone hunts...
CYCLONE_FROM_LEG = 2              # ...but only from the 3rd leg on (0-based)
HELM_FAVOR = 8                    # favor needed to pray to Zeus for Chronos
PRAYER_COST = 3                   # favor spent on a prayer
PROTECT_FAVOR = 13                # favor >= this: Zeus keeps the voyage alive
PROTECTED = ("food", "health", "crew", "hull")
ROUGH_CELLS_PER_DAMAGE = 2        # rough water: hull damage every 2 cells

# The 2D game's islands that join the voyage as "other" shores (the rest of
# its encounters are Odyssey episodes we already have).
EXTRA_ISLANDS = {
    4: {"key": "ogygia", "name": "OGYGIA", "book": "BOOK V"},
    5: {"key": "phaeacia", "name": "PHAEACIA", "book": "BOOK VI"},
    7: {"key": "calypso", "name": "CALYPSO'S HAVEN", "book": "BOOK VII"},
}
EXTRA_CHANCE = 0.45               # how often the other shore is one of these

BASE_STEP_SECONDS = 0.32          # seconds per cell with a full crew

GAME_OVER_TEXT = {
    "food": "The last of the food is gone. The crew starves on the open sea.",
    "health": "Odysseus falls. The voyage ends far from home.",
    "crew": "No one is left to row. The ship drifts forever.",
    "hull": "The hull splits apart. The sea takes the ship.",
}


def step_seconds(crew):
    """Fewer crew row slower."""
    crew = max(crew, 0)
    return BASE_STEP_SECONDS / (0.45 + 0.55 * crew / MAX_RESOURCES["crew"])


def omen_level(favor, leg_index=None):
    """clear / subtle / vague. Leg_index None = ignore the early-leg grace."""
    if favor >= CLEAR_OMEN_FAVOR:
        return "clear"
    early = leg_index is not None and leg_index < CYCLONE_FROM_LEG
    if favor <= CYCLONE_FAVOR and not early:
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
    def __init__(self, center, episode, correct, harsh, final=False,
                 encounter=None):
        self.center = center          # (gx, gy), may be fractional
        self.episode = episode        # entry from islands.EPISODES / ITHACA
        self.encounter = encounter    # 2D-game encounter id, or None
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
        if self.encounter is not None:
            enc = ENCOUNTERS[self.encounter]
            return {"story": enc.story,
                    "choices": [{"text": c.label, "detail": c.description}
                                for c in enc.choices]}
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


def _island_spot(rng, near=18.0):
    """Anywhere in the far part of the sea, fully inside the map."""
    margin = ISLAND_RADIUS + 0.6
    return (rng.uniform(margin, WIDTH - 1 - margin),
            rng.uniform(near, LENGTH - 1 - margin - HARBOR_REACH))


def _random_krakens(rng, isles, obstacles, routes, count):
    """One kraken on a random route (so it matters), the rest anywhere."""
    def ok(cell, placed):
        x, y = cell
        return (cell not in obstacles and 6 <= y <= LENGTH - 5
                and math.hypot(x - START[0], y - START[1]) >= 5
                and not any(i.in_harbor(cell) or i.covers(cell) for i in isles)
                and all(math.hypot(x - h["position"][0],
                                   y - h["position"][1]) >= 4 for h in placed))

    hazards = []
    for k in range(count * 40):
        if len(hazards) == count:
            break
        if not hazards:
            route = rng.choice(routes)
            x, y, _ = route[int(rng.uniform(0.25, 0.8) * (len(route) - 1))]
        else:
            x, y = rng.randint(1, WIDTH - 2), rng.randint(6, LENGTH - 5)
        if not ok((x, y), hazards):
            continue
        period = rng.randint(8, 14)
        hazards.append({
            "position": (x, y),
            "radius": rng.choice((0, 1)),
            "period": period,
            "active_duration": max(3, round(period * rng.uniform(0.4, 0.65))),
        })
    return hazards


def generate_leg(index, seed, used_extras=()):
    """Leg `index` (0-based) of the journey with this seed.
    Legs 0..7 have two islands; leg 8 is Ithaca alone. used_extras: 2D-game
    islands already visited this voyage (each appears at most once)."""
    rng = random.Random(seed * 1000 + index)
    final = index >= islands.ROUTE_LEGS
    for _ in range(300):
        if final:
            isles = [Island(_island_spot(rng, near=26.0), islands.ITHACA,
                            True, False, final=True)]
        else:
            correct = islands.EPISODES[index]
            wrong = rng.choice([e for e in islands.EPISODES
                                if e is not correct])
            extras = [k for k in EXTRA_ISLANDS if k not in used_extras]
            encounter = None
            if extras and rng.random() < EXTRA_CHANCE:
                encounter = rng.choice(extras)
                wrong = EXTRA_ISLANDS[encounter]
            a, b = _island_spot(rng), _island_spot(rng)
            while math.hypot(a[0] - b[0], a[1] - b[1]) < 2 * ISLAND_RADIUS + 2:
                b = _island_spot(rng)
            isles = [Island(a, correct, True, False),
                     Island(b, wrong, False, True, encounter=encounter)]

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

        hazards = _random_krakens(rng, isles, obstacles, open_routes,
                                  2 if final else rng.randint(2, 4))
        routes = [planner.plan(START, t, hazards=hazards, start_time=0,
                               max_time=MAX_PLAN_STEPS) for t in targets]
        if all(routes):
            return Leg(index, isles, reefs, obstacles, hazards, routes)
    raise RuntimeError(f"could not build leg {index} for seed {seed}")


# --- rough water: appears as the gods' favor drops ------------------------------

def rough_water_count(favor, leg_index=None):
    level = omen_level(favor, leg_index)
    return {"clear": 0, "subtle": 2, "vague": 4}[level]


def rough_water(leg, favor, rng, leg_index=None):
    """Churning whirlpools [(gx, gy, radius)]: one on a route, the rest
    anywhere. They never block; sailing through them damages the hull."""
    patches = []
    count = rough_water_count(favor, leg_index)
    for k in range(count * 30):
        if len(patches) == count:
            break
        if not patches:
            route = rng.choice(leg.routes)
            x, y, _ = route[int(rng.uniform(0.2, 0.85) * (len(route) - 1))]
        else:
            x, y = rng.uniform(2, WIDTH - 3), rng.uniform(6, LENGTH - 6)
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


# --- Chronos takes the helm ---------------------------------------------------

HELM_STRATEGIES = ("survival", "balanced", "speed")   # the 2D game's fates


def helm_route(leg, cell, start_step, strategy="balanced"):
    """Plan from the ship's cell at a whole step to the true island's harbor
    with the 2D game's strategy planner. If the cell is under a kraken at
    that step, try the next few steps (the ship holds position meanwhile)."""
    correct = next(k for k, i in enumerate(leg.islands) if i.correct)
    target = leg.routes[correct][-1][:2]
    planner = StrategyPlanner(WIDTH, LENGTH, leg.obstacles)
    for wait in range(4):
        path = planner.plan_strategy(cell, target, hazards=leg.hazards,
                                     strategy=strategy,
                                     start_time=start_step + wait,
                                     max_time=start_step + wait +
                                     MAX_PLAN_STEPS)
        if path:
            return path
    return None


class _EncounterInventory:
    """The 2D game's encounter rules read and change these fields."""

    def __init__(self, resources):
        self.food = resources["food"] / RATION_FOOD
        self.wood = resources["wood"]
        self.rope = resources["rope"]
        self.medicine = resources["medicine"]
        self.morale = resources["favor"] * 10
        self.crew = resources["crew"]
        self.failed = False


class _EncounterShip:
    def __init__(self, hull):
        self.hull = hull
        self.max_hull = MAX_RESOURCES["hull"]

    @property
    def sunk(self):
        return self.hull <= 0


# --- the journey ---------------------------------------------------------------

class Journey:
    def __init__(self, seed):
        self.seed = seed
        self.rng = random.Random(seed)
        self.resources = dict(START_RESOURCES)
        self.leg_index = 0
        self.history = []             # (leg, island name, correct)
        self.encounters = EncounterEngine()     # the 2D game's encounters
        self.used_extras = set()

    @property
    def total_legs(self):
        return islands.ROUTE_LEGS + 1

    def leg(self):
        leg = generate_leg(self.leg_index, self.seed, self.used_extras)
        for island in leg.islands:
            if island.encounter is not None:
                self.used_extras.add(island.encounter)
        return leg

    @property
    def protected(self):
        """Favor above 12: Zeus will not let the voyage end."""
        return self.resources["favor"] >= PROTECT_FAVOR

    def apply(self, effects):
        shielded = self.protected
        for key, delta in effects.items():
            value = self.resources[key] + delta
            floor = 1 if shielded and key in PROTECTED else 0
            self.resources[key] = max(floor, min(MAX_RESOURCES[key], value))

    @property
    def can_pray(self):
        return self.resources["favor"] >= HELM_FAVOR

    def pray(self):
        """Pray to Zeus for Chronos to take the helm. Costs favor."""
        if not self.can_pray:
            return False
        self.apply({"favor": -PRAYER_COST})
        return True

    def choice_order(self, island):
        """The order a card's choices are shown in (the better deal is not
        always first). Same voyage and leg -> same order."""
        rng = random.Random(f"{self.seed}/{self.leg_index}/{island.name}")
        order = list(range(len(island.card["choices"])))
        rng.shuffle(order)
        return order

    def eat(self, seconds):
        self.apply({"food": -FOOD_PER_SECOND * seconds})

    def game_over(self):
        """The reason the voyage ended, or None."""
        if self.protected:
            return None
        for key in PROTECTED:
            if self.resources[key] <= 0:
                return key
        return None

    def resolve(self, island, choice_index):
        """Play a choice on an island card. Returns (result text, effects),
        or (reason, None) if a 2D-game choice can't be afforded."""
        if island.encounter is not None:
            return self._resolve_encounter(island, choice_index)
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

    def _resolve_encounter(self, island, choice_index):
        before = dict(self.resources)
        inv = _EncounterInventory(self.resources)
        ship = _EncounterShip(self.resources["hull"])
        ok, text = self.encounters.resolve(island.encounter, choice_index,
                                           inv, ship)
        if not ok:
            return text, None
        effects = {
            "food": inv.food * RATION_FOOD - before["food"],
            "wood": inv.wood - before["wood"],
            "rope": inv.rope - before["rope"],
            "medicine": inv.medicine - before["medicine"],
            "favor": round(inv.morale / 10) - before["favor"],
            "hull": ship.hull - before["hull"],
        }
        effects = {k: v for k, v in effects.items() if abs(v) > 1e-9}
        self.apply(effects)
        self.history.append((self.leg_index, island.name, island.correct))
        return text, effects

    def loot(self):
        """What the crew finds ashore on every landing."""
        found = {k: self.rng.randint(lo, hi) for k, (lo, hi) in LOOT.items()}
        found = {k: v for k, v in found.items() if v}
        self.apply(found)
        return found

    def repair(self):
        r = self.resources
        if r["wood"] < 2 or r["rope"] < 1:
            return "Repairs need 2 wood and 1 rope. Land on islands to find them."
        if r["hull"] >= MAX_RESOURCES["hull"]:
            return "The hull is already sound."
        self.apply(REPAIR_COST | {"hull": REPAIR_HULL})
        return f"Hull repaired to {r['hull']}   -2 WOOD   -1 ROPE"

    def heal(self):
        r = self.resources
        if r["medicine"] < 1:
            return "No medicine left. Some islands have healing herbs."
        if r["health"] >= MAX_RESOURCES["health"]:
            return "Odysseus is already in good health."
        self.apply(HEAL_COST | {"health": HEAL_HEALTH})
        return f"Medicine taken   +{HEAL_HEALTH} HEALTH   -1 MEDICINE"

    def next_leg(self):
        self.leg_index += 1
