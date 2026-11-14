
import heapq
import math

from core.chronos import ChronosPlanner


STRATEGIES = {
    "survival": {
        "risk_weight": 8.0,
        "wait_cost": 1.0,
    },
    "balanced": {
        "risk_weight": 2.0,
        "wait_cost": 1.0,
    },
    "speed": {
        "risk_weight": 0.0,
        "wait_cost": 1.0,
    },
}


class StrategyPlanner(ChronosPlanner):

        
    def risk_at(self, x, y, t, hazards):
        risk = 0.0

        for hazard in hazards:
            hx, hy = hazard["position"]
            radius = hazard["radius"]
            period = hazard["period"]
            duration = hazard["active_duration"]

            if period <= 0:
                continue

            if t % period >= duration:
                continue

            distance = math.hypot(x - hx, y - hy)

            if distance > radius:
                clearance = distance - radius
                risk += math.exp(-clearance)

        return risk


    def plan_strategy(
        self,
        start,
        goal,
        hazards=None,
        strategy="balanced",
        start_time=0,
        max_time=150,
    ):
        if strategy not in STRATEGIES:
            raise ValueError(
                f"Unknown navigation strategy: {strategy}"
            )

        hazards = hazards or []
        settings = STRATEGIES[strategy]

        if not self.in_bounds(*start):
            return None

        if not self.in_bounds(*goal):
            return None

        initial = (start[0], start[1], start_time)

        if self.is_blocked(*initial, hazards):
            return None

        queue = [
            (self.heuristic(start, goal), 0.0, initial)
        ]

        costs = {initial: 0.0}
        parents = {initial: None}

        actions = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (0, 0),
        ]

        while queue:
            _, current_cost, current = heapq.heappop(queue)

            if current_cost > costs[current]:
                continue

            x, y, t = current

            if (x, y) == goal:
                return self.reconstruct(parents, current)

            if t >= max_time:
                continue

            for dx, dy in actions:
                nx = x + dx
                ny = y + dy
                nt = t + 1

                if not self.in_bounds(nx, ny):
                    continue

                if self.is_blocked(nx, ny, nt, hazards):
                    continue

                risk = self.risk_at(
                    nx, ny, nt, hazards
                )

                step_cost = (
                    1.0
                    + settings["risk_weight"] * risk
                )

                if dx == 0 and dy == 0:
                    step_cost += settings["wait_cost"] - 1.0

                next_state = (nx, ny, nt)
                new_cost = current_cost + step_cost

                if new_cost < costs.get(
                    next_state, float("inf")
                ):
                    costs[next_state] = new_cost
                    parents[next_state] = current

                    priority = (
                        new_cost
                        + self.heuristic((nx, ny), goal)
                    )

                    heapq.heappush(
                        queue,
                        (priority, new_cost, next_state)
                    )

        return None
