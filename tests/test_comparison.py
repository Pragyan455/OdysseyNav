import pytest
from core.comparison import compare_strategies, summarize_route, STRATEGIES


class ExamplePlanner:
    def __init__(self):
        self.calls = []

    def plan_strategy(self, start, goal, hazards, strategy, start_time, max_time):
        self.calls.append((start, goal, tuple(h['position'] for h in hazards),
                           strategy, start_time, max_time))
        if strategy == 'survival':
            return [(0, 0, 0), (0, 1, 1), (1, 1, 2), (2, 1, 3), (2, 0, 4)]
        if strategy == 'balanced':
            return [(0, 0, 0), (1, 0, 1), (1, 0, 2), (2, 0, 3)]
        return [(0, 0, 0), (1, 0, 1), (2, 0, 2)]

    def risk_at(self, x, y, t, hazards):
        return 5.0 if (x, y) == (1, 0) else 0.1


def test_all_three_strategies_are_compared():
    results = compare_strategies(ExamplePlanner(), (0, 0), (2, 0))
    assert tuple(results) == STRATEGIES
    assert all(result.reachable for result in results.values())


def test_same_scenario_for_every_strategy():
    planner = ExamplePlanner()
    hazards = [{'position': (1, 0)}]
    compare_strategies(planner, (0, 0), (2, 0), hazards, start_time=3, max_time=50)
    assert len(planner.calls) == 3
    assert all(call[:3] == ((0, 0), (2, 0), ((1, 0),)) for call in planner.calls)
    assert all(call[-2:] == (3, 50) for call in planner.calls)


def test_time_wait_and_movement_metrics():
    results = compare_strategies(ExamplePlanner(), (0, 0), (2, 0))
    assert results['balanced'].travel_time == 3
    assert results['balanced'].waiting_steps == 1
    assert results['balanced'].movement_steps == 2
    assert results['speed'].travel_time == 2


def test_exposure_is_comparable_and_excludes_initial_state():
    results = compare_strategies(ExamplePlanner(), (0, 0), (2, 0))
    assert results['survival'].storm_exposure == pytest.approx(0.4)
    assert results['speed'].storm_exposure == pytest.approx(5.1)
    assert results['survival'].storm_exposure < results['balanced'].storm_exposure


def test_unreachable_route_is_reported():
    planner = ExamplePlanner()
    result = summarize_route('speed', None, planner, [])
    assert not result.reachable
    assert result.travel_time is None
    assert result.storm_exposure is None
    assert result.waiting_steps == 0


def test_input_path_is_not_mutated():
    planner = ExamplePlanner()
    path = [(0, 0, 0), (1, 0, 1)]
    result = summarize_route('speed', path, planner, [])
    assert path == [(0, 0, 0), (1, 0, 1)]
    assert isinstance(result.path, tuple)
