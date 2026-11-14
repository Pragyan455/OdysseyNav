
from core import scenario, voyage
from core.chronos import ChronosPlanner


def test_same_seed_same_map():
    a = voyage.generate(7, ChronosPlanner)
    b = voyage.generate(7, ChronosPlanner)

    assert a.islands == b.islands
    assert a.hazards == b.hazards
    assert a.path == b.path


def test_different_seeds_differ():
    maps = {tuple(voyage.generate(s, ChronosPlanner).islands)
            for s in range(5)}

    assert len(maps) > 1


def test_every_map_is_solvable_and_safe():
    planner = ChronosPlanner(1, 1)          # only used for is_blocked()

    for seed in range(10):
        v = voyage.generate(seed, ChronosPlanner)

        assert len(v.islands) == voyage.NUM_ISLANDS
        assert len(v.hazards) == voyage.NUM_KRAKENS
        assert v.path[0][:2] == scenario.START
        assert v.path[-1][:2] == scenario.GOAL
        planner.obstacles = v.obstacles
        for x, y, t in v.path:
            assert not planner.is_blocked(x, y, t, v.hazards)


def test_kraken_hits_only_when_up():
    hazard = {"position": (5, 5), "radius": 1, "period": 10,
              "active_duration": 5}

    assert voyage.hazard_hits([hazard], (5, 5), 2.0)       # on
    assert voyage.hazard_hits([hazard], (6, 5), 2.0)       # inside radius
    assert not voyage.hazard_hits([hazard], (7, 5), 2.0)   # outside radius
    assert not voyage.hazard_hits([hazard], (5, 5), 7.0)   # off
