
import pytest

from core.strategy import StrategyPlanner


def test_all_strategies_find_route():
    planner = StrategyPlanner(10, 10)

    for strategy in ("survival", "balanced", "speed"):
        path = planner.plan_strategy(
            (0, 0),
            (9, 9),
            strategy=strategy,
        )

        assert path is not None
        assert path[0][:2] == (0, 0)
        assert path[-1][:2] == (9, 9)


def test_strategies_avoid_blocked_cells():
    planner = StrategyPlanner(
        6, 3,
        obstacles={(2, 1)},
    )

    for strategy in ("survival", "balanced", "speed"):
        path = planner.plan_strategy(
            (0, 1),
            (5, 1),
            strategy=strategy,
        )

        assert path is not None
        assert (2, 1) not in [state[:2] for state in path]


def test_invalid_strategy():
    planner = StrategyPlanner(5, 5)

    with pytest.raises(ValueError):
        planner.plan_strategy(
            (0, 0),
            (4, 4),
            strategy="unknown",
        )


def test_survival_avoids_more_risk():
    planner = StrategyPlanner(7, 5)

    hazards = [{
        "position": (3, 2),
        "radius": 0,
        "period": 100,
        "active_duration": 100,
    }]

    speed_path = planner.plan_strategy(
        (0, 1), (6, 1),
        hazards=hazards,
        strategy="speed",
        max_time=30,
    )

    survival_path = planner.plan_strategy(
        (0, 1), (6, 1),
        hazards=hazards,
        strategy="survival",
        max_time=30,
    )

    assert speed_path is not None
    assert survival_path is not None

    def exposure(path):
        return sum(
            planner.risk_at(x, y, t, hazards)
            for x, y, t in path[1:]
        )

    assert exposure(survival_path) < exposure(speed_path)
