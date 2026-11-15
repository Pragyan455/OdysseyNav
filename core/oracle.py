"""Deterministic, evidence-based interpretation of strategy comparison metrics.

Exposure is a relative accumulated risk score, never a probability.
"""
from dataclasses import dataclass
import math

STRATEGIES = ("survival", "balanced", "speed")


@dataclass(frozen=True)
class OracleVerdict:
    reachable: tuple[str, ...]
    unreachable: tuple[str, ...]
    fastest: tuple[str, ...]
    safest: tuple[str, ...]
    fewest_waits: tuple[str, ...]
    pareto_optimal: tuple[str, ...]
    summary: str


def _winners(results, names, metric):
    if not names:
        return ()
    best = min(getattr(results[name], metric) for name in names)
    return tuple(name for name in names if math.isclose(
        getattr(results[name], metric), best, rel_tol=1e-9, abs_tol=1e-9))


def analyze_strategies(results):
    """Return tied winners and nondominated routes for arrival time and exposure.

    Uses *actual* measured route metrics; does not assume any named strategy wins.
    """
    if not all(name in results for name in STRATEGIES):
        raise ValueError("Expected survival, balanced, and speed comparison results")
    reachable = tuple(name for name in STRATEGIES if results[name].reachable)
    unreachable = tuple(name for name in STRATEGIES if not results[name].reachable)
    if not reachable:
        return OracleVerdict((), unreachable, (), (), (), (),
                             "No strategy found a safe route to Ithaca.")
    fastest = _winners(results, reachable, "travel_time")
    safest = _winners(results, reachable, "storm_exposure")
    fewest_waits = _winners(results, reachable, "waiting_steps")
    pareto = []
    for candidate in reachable:
        t = results[candidate].travel_time
        r = results[candidate].storm_exposure
        dominated = any(
            (results[other].travel_time <= t and results[other].storm_exposure <= r)
            and (results[other].travel_time < t or results[other].storm_exposure < r)
            and not (math.isclose(results[other].travel_time, t, abs_tol=1e-9)
                     and math.isclose(results[other].storm_exposure, r, abs_tol=1e-9))
            for other in reachable if other != candidate
        )
        if not dominated:
            pareto.append(candidate)
    if set(fastest) & set(safest):
        summary = "One or more routes share the best travel time and lowest exposure."
    else:
        summary = "Faster arrival trades off against lower storm exposure."
    if unreachable:
        summary += " Some strategies could not reach Ithaca."
    return OracleVerdict(reachable, unreachable, fastest, safest,
                         fewest_waits, tuple(pareto), summary)
