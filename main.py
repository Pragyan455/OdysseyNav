import math
import pygame

from core.chronos import ChronosPlanner
from core.navigator import Navigator

pygame.init()

WIDTH, HEIGHT = 1200, 750
FPS = 60
CELL_SIZE = 25
GRID_WIDTH = WIDTH // CELL_SIZE
GRID_HEIGHT = HEIGHT // CELL_SIZE

OCEAN = (8, 22, 38)
GOLD = (218, 175, 104)
WHITE = (230, 224, 210)
MUTED = (120, 145, 160)
ISLAND = (63, 83, 91)
DANGER = (175, 65, 70)
SAFE = (55, 125, 115)
PANEL = (5, 15, 27)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ODYSSEY | The Fractured Sea")
clock = pygame.time.Clock()
font_title = pygame.font.SysFont("georgia", 34)
font_normal = pygame.font.SysFont("georgia", 18)
font_small = pygame.font.SysFont("consolas", 14)

START = (5, 15)
GOAL = (41, 15)
DEMO_MODE = False
PASSAGE_Y = START[1]
PASSAGE_START = 10
PASSAGE_END = 37

islands = [(360, 250, 65), (580, 440, 85), (790, 260, 75)]


def grid_to_world(x, y):
    return pygame.Vector2(x * CELL_SIZE + CELL_SIZE / 2,
                          y * CELL_SIZE + CELL_SIZE / 2)


def create_obstacles():
    blocked = set()
    if DEMO_MODE:
        # In the demo, a straight, visibly marked channel is the only
        # passage through the central part of the map.
        for gx in range(PASSAGE_START, PASSAGE_END + 1):
            for gy in range(GRID_HEIGHT):
                if gy != PASSAGE_Y:
                    blocked.add((gx, gy))
        return blocked

    for gx in range(GRID_WIDTH):
        for gy in range(GRID_HEIGHT):
            position = grid_to_world(gx, gy)
            for ix, iy, radius in islands:
                if position.distance_to((ix, iy)) < radius + 20:
                    blocked.add((gx, gy))
                    break
    return blocked


def build_world():
    global obstacles, planner, hazards, path, navigator
    global ship, ithaca, simulation_time, paused

    obstacles = create_obstacles()
    planner = ChronosPlanner(GRID_WIDTH, GRID_HEIGHT, obstacles)

    if DEMO_MODE:
        # Single-cell storm in a constrained channel: demonstrates waiting.
        hazards = [{
            "position": (24, PASSAGE_Y),
            "radius": 0,
            "period": 12,
            "active_duration": 8,
        }]
    else:
        # The original open sea, with islands and a larger temporal anomaly.
        hazards = [{
            "position": (670 // CELL_SIZE, 260 // CELL_SIZE),
            "radius": 2,
            "period": 12,
            "active_duration": 6,
        }]

    path = planner.plan(START, GOAL, hazards=hazards,
                        start_time=0, max_time=150)
    navigator = Navigator(path)
    ship = grid_to_world(*START)
    ithaca = grid_to_world(*GOAL)
    simulation_time = 0.0
    paused = True

    if path:
        waits = sum(a[:2] == b[:2] for a, b in zip(path, path[1:]))
        print(f"{'DEMO' if DEMO_MODE else 'CINEMATIC'}: "
              f"{len(path)} states, {waits} waiting steps")
    else:
        print("Chronos: no safe route found")


build_world()


def get_ship_position(t):
    if not path:
        return grid_to_world(*START)
    if t <= path[0][2]:
        return grid_to_world(*path[0][:2])
    for previous, following in zip(path, path[1:]):
        x1, y1, t1 = previous
        x2, y2, t2 = following
        if t1 <= t < t2:
            progress = (t - t1) / (t2 - t1)
            return grid_to_world(x1, y1).lerp(grid_to_world(x2, y2), progress)
    return grid_to_world(*path[-1][:2])


def navigation_status():
    if not path:
        return "NO ROUTE"
    if navigator.finished:
        return "ARRIVED"
    if paused:
        return "PAUSED"
    if navigator.index + 1 < len(path):
        if path[navigator.index][:2] == path[navigator.index + 1][:2]:
            return "WAITING"
    return "SAILING"


def storm_active(t):
    hazard = hazards[0]
    return int(t) % hazard["period"] < hazard["active_duration"]


def storm_countdown(t):
    hazard = hazards[0]
    phase = t % hazard["period"]
    if phase < hazard["active_duration"]:
        return "STORM CLEARS IN", hazard["active_duration"] - phase
    return "STORM RETURNS IN", hazard["period"] - phase


def draw_text(message, font, color, position):
    screen.blit(font.render(message, True, color), position)


def draw_ocean(t):
    screen.fill(OCEAN)
    for y in range(110, HEIGHT - 70, 32):
        for x in range(0, WIDTH, 95):
            offset = math.sin(t * 0.8 + x * 0.02 + y * 0.01) * 8
            pygame.draw.line(screen, (17, 42, 59),
                             (x + offset, y), (x + 48 + offset, y), 1)


def draw_islands():
    if DEMO_MODE:
        # Show the passage without rendering islands that are absent
        # from the demo's collision map.
        channel_y = int(grid_to_world(0, PASSAGE_Y).y)
        left = int(grid_to_world(PASSAGE_START, 0).x - CELL_SIZE / 2)
        right = int(grid_to_world(PASSAGE_END, 0).x + CELL_SIZE / 2)
        pygame.draw.rect(screen, (25, 43, 53),
                         (left, channel_y - CELL_SIZE / 2 - 9,
                          right - left, CELL_SIZE + 18), 1)
        pygame.draw.line(screen, MUTED, (left, channel_y - CELL_SIZE / 2),
                         (right, channel_y - CELL_SIZE / 2), 1)
        pygame.draw.line(screen, MUTED, (left, channel_y + CELL_SIZE / 2),
                         (right, channel_y + CELL_SIZE / 2), 1)
        draw_text("THE NARROWS", font_small, MUTED, (left + 10, channel_y - 44))
        return

    for x, y, radius in islands:
        pygame.draw.circle(screen, (25, 43, 53), (x, y), radius + 9)
        pygame.draw.circle(screen, ISLAND, (x, y), radius)
        pygame.draw.circle(screen, GOLD, (x, y), radius, 1)


def draw_navigation_path():
    if not path:
        return
    points = [grid_to_world(x, y) for x, y, _ in path]
    if len(points) >= 2:
        pygame.draw.lines(screen, GOLD, False, points, 2)
    for point in points[::4]:
        pygame.draw.circle(screen, WHITE, (round(point.x), round(point.y)), 3)


def draw_ship(t):
    x, y = ship.x, ship.y + math.sin(t * 2) * 3
    pygame.draw.polygon(screen, GOLD, [
        (x - 24, y - 12), (x + 28, y), (x - 24, y + 12), (x - 12, y)
    ])
    pygame.draw.line(screen, WHITE, (x - 4, y - 18), (x - 4, y + 18), 2)
    pygame.draw.circle(screen, GOLD, (int(x), int(y)), 30, 1)


def draw_ithaca():
    x, y = int(ithaca.x), int(ithaca.y)
    pygame.draw.circle(screen, GOLD, (x, y), 36, 2)
    pygame.draw.circle(screen, GOLD, (x, y), 6)
    draw_text("ITHACA", font_normal, GOLD, (x - 35, y + 48))


def draw_anomaly(t):
    active = storm_active(t)
    color = DANGER if active else SAFE

    if DEMO_MODE:
        center = grid_to_world(*hazards[0]["position"])
        x, y = round(center.x), round(center.y)
        pygame.draw.rect(screen, color,
                         (x - CELL_SIZE // 2, y - CELL_SIZE // 2,
                          CELL_SIZE, CELL_SIZE), 2)
        pygame.draw.circle(screen, color, (x, y), 5)
    else:
        # Original cinematic storm position and circular appearance.
        x, y = 670, 260
        radius = round(43 + math.sin(t * 2) * 6)
        pygame.draw.circle(screen, color, (x, y), radius, 2)
        pygame.draw.circle(screen,
                           (95, 40, 55) if active else (30, 75, 75),
                           (x, y), 23)

    label = "TEMPORAL STORM: ACTIVE" if active else "TEMPORAL STORM: DORMANT"
    draw_text(label, font_small, color, (x - 95, y - 75))


def draw_interface():
    pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, 92))
    pygame.draw.line(screen, GOLD, (0, 92), (WIDTH, 92), 1)
    draw_text("ODYSSEY", font_title, GOLD, (35, 18))
    draw_text("THE FRACTURED SEA", font_small, MUTED, (38, 63))
    draw_text("MODE: " + ("CHRONOS DEMO" if DEMO_MODE else "CINEMATIC"),
              font_small, MUTED, (365, 28))

    status = navigation_status()
    draw_text(f"CHRONOS ENGINE: {status}", font_small, GOLD, (840, 28))
    draw_text(f"SIMULATION TIME: {simulation_time:06.1f}",
              font_small, WHITE, (840, 54))
    remaining = max(0, len(path) - navigator.index - 1) if path else 0
    draw_text(f"ROUTE STEPS REMAINING: {remaining}",
              font_small, MUTED, (570, 54))

    if status == "WAITING":
        draw_text("POSEIDON BLOCKS THE PASSAGE — HOLD POSITION",
                  font_small, DANGER, (325, 110))
    elif status == "ARRIVED":
        draw_text("MISSION COMPLETE — ITHACA REACHED",
                  font_normal, GOLD, (375, 110))
    elif status == "NO ROUTE":
        draw_text("NO SAFE ROUTE — CHECK THE NAVIGATION MAP",
                  font_small, DANGER, (340, 110))

    pygame.draw.rect(screen, PANEL, (0, HEIGHT - 70, WIDTH, 70))
    pygame.draw.line(screen, GOLD, (0, HEIGHT - 70), (WIDTH, HEIGHT - 70), 1)
    draw_text("SPACE: START / PAUSE", font_small, WHITE, (35, HEIGHT - 42))
    draw_text("R: RESET", font_small, WHITE, (260, HEIGHT - 42))
    draw_text("1: SEA  2: DEMO", font_small, WHITE, (360, HEIGHT - 42))
    label, countdown = storm_countdown(simulation_time)
    draw_text(f"{label}: {countdown:.1f}s", font_small,
              DANGER if storm_active(simulation_time) else SAFE,
              (590, HEIGHT - 42))
    draw_text("ITHACA", font_small, GOLD, (1060, HEIGHT - 42))

running = True

while running:
    dt = clock.tick(FPS) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE and path and not navigator.finished:
                paused = not paused
            elif event.key in (pygame.K_1, pygame.K_2):
                selected_demo = event.key == pygame.K_2
                if DEMO_MODE != selected_demo:
                    DEMO_MODE = selected_demo
                    build_world()
            elif event.key == pygame.K_r:
                simulation_time = 0.0
                paused = True
                navigator.reset()
                ship.update(grid_to_world(*START))

    if not paused and path:
        simulation_time += dt
        navigator.update(simulation_time)
        ship.update(get_ship_position(simulation_time))
        if navigator.finished:
            paused = True
            ship.update(grid_to_world(*GOAL))

    draw_ocean(simulation_time)
    draw_islands()
    draw_navigation_path()
    draw_ithaca()
    draw_anomaly(simulation_time)
    draw_ship(simulation_time)
    draw_interface()
    pygame.display.flip()

pygame.quit()
