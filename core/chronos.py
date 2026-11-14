
import heapq
import math


class ChronosPlanner:
    def __init__(self, width, height, obstacles=None):
        self.width = width
        self.height = height
        self.obstacles = set(obstacles or [])

    def heuristic(self, a, b):
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def in_bounds(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def is_blocked(self, x, y, t, hazards):
        if (x, y) in self.obstacles:
            return True

        for hazard in hazards:
            hx, hy = hazard["position"]
            radius = hazard["radius"]
            period = hazard["period"]
            active_duration = hazard["active_duration"]

            if period <= 0:
                continue

            active = (t % period) < active_duration

            if active and math.hypot(x - hx, y - hy) <= radius:
                return True

        return False

    def plan(self, start, goal, hazards=None, start_time=0,
             max_time=300):
        hazards = hazards or []

        start_state = (start[0], start[1], start_time)

        queue = [(self.heuristic(start, goal), 0, start_state)]
        came_from = {start_state: None}
        cost_so_far = {start_state: 0}

        # Four directions plus waiting in place
        actions = [
            (1, 0),
            (-1, 0),
            (0, 1),
            (0, -1),
            (0, 0),
        ]

        while queue:
            _, current_cost, current = heapq.heappop(queue)
            x, y, t = current

            if current_cost > cost_so_far[current]:
                continue

            if (x, y) == goal:
                return self.reconstruct(came_from, current)

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

                next_state = (nx, ny, nt)
                new_cost = current_cost + 1

                if (next_state not in cost_so_far or
                        new_cost < cost_so_far[next_state]):

                    cost_so_far[next_state] = new_cost
                    priority = new_cost + self.heuristic(
                        (nx, ny), goal
                    )

                    heapq.heappush(
                        queue,
                        (priority, new_cost, next_state)
                    )

                    came_from[next_state] = current

        return None

    def reconstruct(self, came_from, state):
        path = []

        while state is not None:
            path.append(state)
            state = came_from[state]

        path.reverse()
        return path
