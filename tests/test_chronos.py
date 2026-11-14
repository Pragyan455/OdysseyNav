
from core.chronos import ChronosPlanner


def test_basic_navigation():
    planner = ChronosPlanner(10, 10)

    path = planner.plan(
        start=(0, 0),
        goal=(9, 9)
    )

    assert path is not None
    assert path[0][:2] == (0, 0)
    assert path[-1][:2] == (9, 9)


def test_static_obstacle():
    obstacles = {(2, 2), (2, 3), (2, 4)}

    planner = ChronosPlanner(10, 10, obstacles)

    path = planner.plan(
        start=(0, 3),
        goal=(5, 3)
    )

    assert path is not None

    for x, y, t in path:
        assert (x, y) not in obstacles


def test_temporal_hazard():
    planner = ChronosPlanner(5, 1)

    hazards = [
        {
            "position": (2, 0),
            "radius": 0,
            "period": 6,
            "active_duration": 4,
        }
    ]

    path = planner.plan(
        start=(0, 0),
        goal=(4, 0),
        hazards=hazards,
        max_time=30
    )

    assert path is not None

    for x, y, t in path:
        assert not planner.is_blocked(x, y, t, hazards)


def test_unreachable_goal():
    planner = ChronosPlanner(
        3, 3,
        obstacles={(1, 0), (1, 1), (1, 2)}
    )

    path = planner.plan(
        start=(0, 1),
        goal=(2, 1),
        max_time=20
    )

    assert path is None
