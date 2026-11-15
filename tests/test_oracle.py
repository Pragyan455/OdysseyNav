import pytest
from core.comparison import RouteMetrics
from core.oracle import analyze_strategies


def route(name, time, risk, waits=0):
    if time is None:
        return RouteMetrics(name, (), None, None, 0, 0, None)
    return RouteMetrics(name, ((0, 0, 0), (1, 0, time)), time, time,
                        1, waits, risk)


def test_identifies_fastest_and_safest_from_metrics():
    verdict = analyze_strategies({
        'survival': route('survival', 10, 0.1),
        'balanced': route('balanced', 8, 0.3),
        'speed': route('speed', 5, 0.8),
    })
    assert verdict.fastest == ('speed',)
    assert verdict.safest == ('survival',)
    assert set(verdict.pareto_optimal) == {'survival', 'balanced', 'speed'}


def test_ties_are_reported_not_arbitrarily_broken():
    verdict = analyze_strategies({
        'survival': route('survival', 5, 0.2),
        'balanced': route('balanced', 5, 0.2),
        'speed': route('speed', 8, 0.5),
    })
    assert verdict.fastest == ('survival', 'balanced')
    assert verdict.safest == ('survival', 'balanced')
    assert verdict.pareto_optimal == ('survival', 'balanced')


def test_unreachable_is_excluded():
    verdict = analyze_strategies({
        'survival': route('survival', None, None),
        'balanced': route('balanced', 9, 0.1),
        'speed': route('speed', 6, 0.5),
    })
    assert verdict.unreachable == ('survival',)
    assert verdict.fastest == ('speed',)
    assert verdict.safest == ('balanced',)


def test_no_routes():
    verdict = analyze_strategies({name: route(name, None, None)
                                  for name in ('survival', 'balanced', 'speed')})
    assert not verdict.reachable
    assert not verdict.fastest
    assert 'No strategy' in verdict.summary


def test_dominated_route_is_not_pareto_optimal():
    verdict = analyze_strategies({
        'survival': route('survival', 6, 0.2),
        'balanced': route('balanced', 8, 0.5),
        'speed': route('speed', 5, 0.9),
    })
    assert 'balanced' not in verdict.pareto_optimal
    assert verdict.pareto_optimal == ('survival', 'speed')


def test_fewest_waits_includes_ties():
    verdict = analyze_strategies({
        'survival': route('survival', 7, 0.1, 2),
        'balanced': route('balanced', 6, 0.3, 0),
        'speed': route('speed', 5, 0.5, 0),
    })
    assert verdict.fewest_waits == ('balanced', 'speed')


def test_missing_strategy_raises():
    with pytest.raises(ValueError):
        analyze_strategies({'survival': route('survival', 5, 0.1)})
