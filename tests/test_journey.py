
import math
import random

from core import islands, journey
from core.chronos import ChronosPlanner


def test_every_leg_is_passable_for_many_seeds():
    checker = ChronosPlanner(1, 1)
    for seed in range(6):
        for index in range(islands.ROUTE_LEGS + 1):
            leg = journey.generate_leg(index, seed)
            checker.obstacles = leg.obstacles
            for island, route in zip(leg.islands, leg.routes):
                assert route[0][:2] == journey.START
                assert leg.landed(route[-1][:2]) is island
                for x, y, t in route:
                    assert not checker.is_blocked(x, y, t, leg.hazards)


def test_legs_follow_the_odyssey():
    for index, episode in enumerate(islands.EPISODES):
        leg = journey.generate_leg(index, seed=3)
        correct = [i for i in leg.islands if i.correct]
        wrong = [i for i in leg.islands if not i.correct]
        assert len(leg.islands) == 2
        assert correct[0].episode is episode and not correct[0].harsh
        assert wrong[0].episode is not episode and wrong[0].harsh
    final = journey.generate_leg(islands.ROUTE_LEGS, seed=3)
    assert final.final and final.islands[0].name == "ITHACA"


def test_same_seed_same_leg():
    a, b = journey.generate_leg(2, 9), journey.generate_leg(2, 9)
    assert a.obstacles == b.obstacles and a.hazards == b.hazards


def test_resources_clamp_and_game_over():
    j = journey.Journey(1)
    j.apply({"food": 100, "crew": -3})
    assert j.resources["food"] == journey.MAX_RESOURCES["food"]
    assert j.resources["crew"] == 9
    assert j.game_over() is None
    j.apply({"health": -50})
    assert j.resources["health"] == 0 and j.game_over() == "health"


def test_food_drains_per_second():
    j = journey.Journey(1)
    j.eat(10)
    assert math.isclose(j.resources["food"],
                        30 - 10 * journey.FOOD_PER_SECOND)


def test_choices_resolve_with_text():
    j = journey.Journey(5)
    leg = j.leg()
    for island in leg.islands:
        if island.encounter is not None:
            continue                       # once per voyage: tested below
        for k in range(len(island.card["choices"])):
            text, effects = j.resolve(island, k)
            assert text and isinstance(effects, dict)


def test_every_card_is_well_formed():
    for ep in islands.EPISODES:
        for version in ("calm", "harsh"):
            card = ep[version]
            assert card["story"] and len(card["choices"]) == 2
            for c in card["choices"]:
                keys = (c.get("effects", {}) | c.get("win", {}) |
                        c.get("lose", {}))
                assert set(keys) <= set(journey.START_RESOURCES)


def test_omens_and_speed():
    assert journey.omen_level(8) == "clear"
    assert journey.omen_level(5) == "subtle"
    assert journey.omen_level(2) == "vague"
    assert journey.step_seconds(12) < journey.step_seconds(6)


def test_cyclone_landing_is_safe():
    rng = random.Random(2)
    leg = journey.generate_leg(1, 4)
    water = journey.reachable_water(leg)
    for _ in range(20):
        cell = journey.safe_landing(rng, leg, (10, 30))
        assert cell in water and not leg.landed(cell)
        assert math.hypot(cell[0] - 10, cell[1] - 30) >= 8


def test_kraken_hits_only_when_up():
    h = {"position": (5, 5), "radius": 1, "period": 10, "active_duration": 5}
    assert journey.hazard_hits([h], (6, 5), 2.0)
    assert not journey.hazard_hits([h], (7, 5), 2.0)
    assert not journey.hazard_hits([h], (5, 5), 7.0)


def test_rough_water_grows_as_favor_drops():
    leg = journey.generate_leg(2, 7)
    counts = [len(journey.rough_water(leg, f, random.Random(1)))
              for f in (9, 5, 2)]
    assert counts[0] == 0 and 0 < counts[1] <= counts[2]
    for x, y, r in journey.rough_water(leg, 2, random.Random(1)):
        assert not journey.in_rough_water([(x, y, r)], journey.START)
        assert journey.in_rough_water([(x, y, r)], (round(x), round(y)))


# --- merged from the 2D game: hull, materials, its islands, Chronos helm ----

def find_extra_leg():
    for seed in range(40):
        for index in range(islands.ROUTE_LEGS):
            leg = journey.generate_leg(index, seed)
            for isle in leg.islands:
                if isle.encounter is not None:
                    return seed, index, isle
    raise AssertionError("no 2D-game island in 40 seeds")


def test_2d_islands_appear_once_per_voyage():
    for seed in range(8):
        j, seen = journey.Journey(seed), []
        for _ in range(islands.ROUTE_LEGS):
            seen += [i.encounter for i in j.leg().islands
                     if i.encounter is not None]
            j.next_leg()
        assert len(seen) == len(set(seen))
        assert set(seen) <= set(journey.EXTRA_ISLANDS)


def test_2d_encounter_effects_map_onto_our_resources():
    seed, index, isle = find_extra_leg()
    j = journey.Journey(seed)
    j.resources.update(food=20.0, wood=3, rope=2, favor=6, hull=60)
    before = dict(j.resources)
    text, effects = j.resolve(isle, 1)
    assert text and effects is not None
    for key, delta in effects.items():
        assert math.isclose(j.resources[key], before[key] + delta)
    again, none = j.resolve(isle, 0)       # once per voyage
    assert none is None


def test_unaffordable_2d_choice_keeps_the_card_open():
    j = journey.Journey(1)
    phaeacia = journey.Island((5, 30), journey.EXTRA_ISLANDS[5], False, True,
                              encounter=5)
    j.resources.update(food=1.0, wood=0)
    text, effects = j.resolve(phaeacia, 0)  # needs 2 rations
    assert effects is None and "Need" in text
    assert j.encounters.available(5)


def test_repair_and_heal():
    j = journey.Journey(1)
    assert "need" in j.repair().lower()
    j.resources.update(wood=2, rope=1, hull=40)
    j.repair()
    assert j.resources["hull"] == 40 + journey.REPAIR_HULL
    assert (j.resources["wood"], j.resources["rope"]) == (0, 0)
    j.resources.update(medicine=1, health=5)
    j.heal()
    assert j.resources["health"] == 5 + journey.HEAL_HEALTH
    assert j.resources["medicine"] == 0


def test_hull_zero_ends_the_voyage():
    j = journey.Journey(1)
    j.apply(journey.KRAKEN_DAMAGE)
    assert j.resources["hull"] < journey.MAX_RESOURCES["hull"]
    j.apply({"hull": -1000})
    assert j.game_over() == "hull"


def test_loot_on_landing():
    j = journey.Journey(3)
    found = j.loot()
    for k, v in found.items():
        lo, hi = journey.LOOT[k]
        assert lo <= v <= hi and j.resources[k] >= v


def test_chronos_helm_reaches_the_true_island_safely():
    checker = ChronosPlanner(1, 1)
    for seed in range(4):
        leg = journey.generate_leg(seed, seed)
        checker.obstacles = leg.obstacles
        correct = next(i for i in leg.islands if i.correct)
        for strategy in journey.HELM_STRATEGIES:
            path = journey.helm_route(leg, journey.START, 3, strategy)
            assert path and leg.landed(path[-1][:2]) is correct
            assert path[0][:2] == journey.START and path[0][2] >= 3
            for x, y, t in path:
                assert not checker.is_blocked(x, y, t, leg.hazards)


# --- favor rework, prayer, protection, randomness ------------------------------

def test_favor_starts_at_zero_and_zero_favor_does_not_end_the_voyage():
    j = journey.Journey(1)
    assert j.resources["favor"] == 0
    assert j.game_over() is None
    j.apply({"favor": -5})
    assert j.resources["favor"] == 0 and j.game_over() is None


def test_early_legs_are_spared_the_cyclone():
    assert journey.omen_level(0, leg_index=0) == "subtle"
    assert journey.omen_level(0, leg_index=1) == "subtle"
    assert journey.omen_level(0, leg_index=2) == "vague"
    assert journey.omen_level(journey.CLEAR_OMEN_FAVOR, 0) == "clear"


def test_praying_needs_favor_and_costs_it():
    j = journey.Journey(1)
    j.resources["favor"] = journey.HELM_FAVOR - 1
    assert not j.can_pray and not j.pray()
    assert j.resources["favor"] == journey.HELM_FAVOR - 1
    j.resources["favor"] = journey.HELM_FAVOR
    assert j.pray()
    assert j.resources["favor"] == journey.HELM_FAVOR - journey.PRAYER_COST


def test_high_favor_protects_the_voyage():
    j = journey.Journey(1)
    j.resources["favor"] = journey.PROTECT_FAVOR
    j.apply({"food": -999, "health": -999, "crew": -999, "hull": -999})
    for key in journey.PROTECTED:
        assert j.resources[key] == 1
    assert j.game_over() is None
    j.eat(1000)
    assert j.resources["food"] == 1
    j.resources["favor"] = journey.PROTECT_FAVOR - 1      # protection ends
    j.apply({"crew": -1})
    assert j.game_over() == "crew"


def test_island_positions_vary():
    spots = {tuple(round(c) for c in i.center)
             for seed in range(6) for index in range(4)
             for i in journey.generate_leg(index, seed).islands}
    xs, ys = {x for x, _ in spots}, {y for _, y in spots}
    assert len(spots) > 30 and max(xs) - min(xs) >= 10 and max(ys) - min(ys) >= 10


def test_kraken_positions_vary_and_spread():
    spots = [h["position"] for seed in range(6) for index in range(4)
             for h in journey.generate_leg(index, seed).hazards]
    xs, ys = [x for x, _ in spots], [y for _, y in spots]
    assert len(set(spots)) > 25
    assert max(xs) - min(xs) >= 15 and max(ys) - min(ys) >= 20


def test_choice_order_is_shuffled_but_stable():
    orders = set()
    for seed in range(12):
        j = journey.Journey(seed)
        isle = j.leg().islands[0]
        orders.add(tuple(j.choice_order(isle)))
        assert j.choice_order(isle) == j.choice_order(isle)
    assert orders == {(0, 1), (1, 0)}


def test_some_islands_have_no_safe_choice():
    both_risky = [ep for ep in islands.EPISODES for v in ("calm", "harsh")
                  if all("chance" in c for c in ep[v]["choices"])]
    assert len(both_risky) >= 3
