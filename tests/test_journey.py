
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
