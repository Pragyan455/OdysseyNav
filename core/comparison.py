"""Compare ODYSSEY strategies on identical navigation conditions."""
from dataclasses import dataclass

STRATEGIES = ("survival", "balanced", "speed")


@dataclass(frozen=True)
class RouteMetrics:
    strategy: str
    path: tuple
    arrival_time: float | None
    travel_time: float | None
    movement_steps: int
    waiting_steps: int
    storm_exposure: float | None

    @property
    def reachable(self):
        return bool(self.path)


def summarize_route(strategy, path, planner, hazards):
    """Summarize a timed path. Exposure is a relative risk score, not probability."""
    if not path:
        return RouteMetrics(strategy, (), None, None, 0, 0, None)
    states = tuple(tuple(state) for state in path)
    waits = sum(a[:2] == b[:2] for a, b in zip(states, states[1:]))
    exposure = sum(planner.risk_at(x, y, t, hazards) for x, y, t in states[1:])
    return RouteMetrics(strategy, states, states[-1][2],
                        states[-1][2] - states[0][2],
                        len(states) - 1 - waits, waits, exposure)


def compare_strategies(planner, start, goal, hazards=None, start_time=0, max_time=150):
    """Plan each strategy independently with the same map and storm schedule."""
    hazards = list(hazards or [])
    results = {}
    for strategy in STRATEGIES:
        path = planner.plan_strategy(start, goal, hazards=hazards,
                                     strategy=strategy, start_time=start_time,
                                     max_time=max_time)
        results[strategy] = summarize_route(strategy, path, planner, hazards)
    return results
