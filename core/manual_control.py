"""Frame-rate-independent ship steering and collision checks (no Pygame required)."""
import math


class ManualShip:
    def __init__(self, x, y, heading=0.0, speed=0.0):
        self.x = float(x)
        self.y = float(y)
        self.heading = float(heading)  # degrees, 0 points right; positive clockwise on screen
        self.speed = float(speed)  # pixels per second

    def step(self, dt, throttle, rudder, blocked, width, height,
             acceleration=65.0, drag=0.7, max_forward=95.0,
             max_reverse=35.0, turn_rate=125.0):
        """Update position; reject movement into blocked cells or off-map."""
        dt = max(0.0, min(float(dt), 0.1))
        throttle = max(-1.0, min(1.0, float(throttle)))
        rudder = max(-1.0, min(1.0, float(rudder)))
        self.speed += throttle * acceleration * dt
        if throttle == 0:
            self.speed *= max(0.0, 1.0 - drag * dt)
        self.speed = max(-max_reverse, min(max_forward, self.speed))
        steer_factor = 0.35 + 0.65 * min(abs(self.speed) / max_forward, 1.0)
        self.heading = (self.heading + rudder * turn_rate * steer_factor * dt) % 360
        angle = math.radians(self.heading)
        nx = self.x + math.cos(angle) * self.speed * dt
        ny = self.y + math.sin(angle) * self.speed * dt
        if 0 <= nx < width and 0 <= ny < height and not blocked(nx, ny):
            self.x, self.y = nx, ny
            return True
        self.speed = 0.0
        return False
