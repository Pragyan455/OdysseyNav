import math
import pygame

from core.strategy import StrategyPlanner
from core.navigator import Navigator
from core.narrative import NarrativeEngine
from core.timeline import VoyageTimeline
from core.comparison import compare_strategies

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
STRATEGY_COLORS = {
    "survival": (90, 195, 163),
    "balanced": (109, 165, 220),
    "speed": (236, 173, 92),
}

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ODYSSEY | The Fractured Sea")
clock = pygame.time.Clock()
font_title = pygame.font.SysFont("georgia", 34)
font_normal = pygame.font.SysFont("georgia", 18)
font_small = pygame.font.SysFont("consolas", 14)

START = (5, 15)
GOAL = (41, 15)
DEMO_MODE = False
STRATEGY = "balanced"
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
    global ship, ithaca, simulation_time, paused, route_exposure, route_duration
    global narrative, timeline, replay_mode, replay_time
    global comparison_results, comparison_mode

    obstacles = create_obstacles()
    planner = StrategyPlanner(GRID_WIDTH, GRID_HEIGHT, obstacles)

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

    comparison_results = compare_strategies(
        planner, START, GOAL, hazards=hazards, start_time=0, max_time=150
    )
    path = list(comparison_results[STRATEGY].path) or None
    route_duration = path[-1][2] - path[0][2] if path else None
    route_exposure = (
        sum(planner.risk_at(x, y, t, hazards) for x, y, t in path[1:])
        if path else None
    )
    navigator = Navigator(path)
    ship = grid_to_world(*START)
    ithaca = grid_to_world(*GOAL)
    simulation_time = 0.0
    paused = True
    narrative = NarrativeEngine()
    timeline = VoyageTimeline(path, hazards)
    replay_mode = False
    replay_time = 0.0
    comparison_mode = False

    if path:
        waits = sum(a[:2] == b[:2] for a, b in zip(path, path[1:]))
        print(f"{'DEMO' if DEMO_MODE else 'CINEMATIC'} "
              f"| {STRATEGY.upper()} | {len(path)} states | "
              f"{waits} waiting steps | arrival {route_duration}s | "
              f"exposure {route_exposure:.3f}")
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


def draw_comparison_routes():
    """Overlay the three routes; current selection remains highlighted."""
    for strategy in ("survival", "balanced", "speed"):
        result = comparison_results[strategy]
        if not result.reachable:
            continue
        points = [grid_to_world(x, y) for x, y, _ in result.path]
        if len(points) >= 2:
            pygame.draw.lines(screen, STRATEGY_COLORS[strategy], False,
                              points, 4 if strategy == STRATEGY else 2)


def draw_comparison_panel():
    """Display factual route metrics; differences depend on the scenario."""
    panel = pygame.Rect(245, 390, 710, 226)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, GOLD, panel, 1, border_radius=8)
    draw_text("THE COUNCIL OF FATES  |  C: CLOSE", font_normal, GOLD,
              (panel.x + 22, panel.y + 14))
    draw_text("STRATEGY           ARRIVAL     MOVES     WAITS     EXPOSURE",
              font_small, MUTED, (panel.x + 22, panel.y + 60))
    for index, strategy in enumerate(("survival", "balanced", "speed")):
        result = comparison_results[strategy]
        y = panel.y + 91 + index * 37
        selected = "*" if strategy == STRATEGY else " "
        if result.reachable:
            values = (f"{result.travel_time:>5.0f}s"
                      f"        {result.movement_steps:>3}"
                      f"        {result.waiting_steps:>3}"
                      f"        {result.storm_exposure:>7.2f}")
        else:
            values = "NO SAFE ROUTE"
        draw_text(f"{selected} {strategy.upper():<10}", font_small,
                  STRATEGY_COLORS[strategy], (panel.x + 22, y))
        draw_text(values, font_small, WHITE, (panel.x + 196, y))
    draw_text("Exposure is a relative risk score, not a probability.",
              font_small, MUTED, (panel.x + 22, panel.bottom - 25))


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


def draw_narrative():
    if narrative.current is None:
        return
    message = narrative.current.text
    rendered = font_normal.render(message, True, GOLD)
    center_x = WIDTH // 2
    box_width = rendered.get_width() + 48
    box = pygame.Rect(center_x - box_width // 2, 186, box_width, 48)
    pygame.draw.rect(screen, PANEL, box, border_radius=6)
    pygame.draw.rect(screen, GOLD, box, 1, border_radius=6)
    screen.blit(rendered, rendered.get_rect(center=box.center))


def draw_timeline():
    if not path:
        return
    x0, x1, y = 220, WIDTH - 220, HEIGHT - 114
    pygame.draw.rect(screen, PANEL, (x0 - 20, y - 36, x1 - x0 + 40, 72), border_radius=6)
    pygame.draw.line(screen, MUTED, (x0, y), (x1, y), 3)
    duration = max(0.001, timeline.end - timeline.start)
    for step in range(int(timeline.start), int(timeline.end) + 1):
        frame = timeline.frame(step + 0.001)
        if frame.storm_active:
            px = x0 + (step - timeline.start) / duration * (x1 - x0)
            pygame.draw.line(screen, DANGER, (px, y - 5), (px, y + 5), 2)
    for wait_time in timeline.wait_times:
        px = x0 + (wait_time - timeline.start) / duration * (x1 - x0)
        pygame.draw.circle(screen, GOLD, (round(px), y), 5)
    shown_time = replay_time if replay_mode else simulation_time
    shown_time = timeline.clamp(shown_time)
    px = x0 + (shown_time - timeline.start) / duration * (x1 - x0)
    pygame.draw.circle(screen, WHITE, (round(px), y), 8)
    label = "REPLAY" if replay_mode else "VOYAGE TIMELINE"
    draw_text(f"{label}  {shown_time:.1f}s / {timeline.end:.0f}s", font_small,
              GOLD, (x0, y - 30))
    draw_text("RED: STORM   GOLD: WAIT", font_small, MUTED, (x1 - 210, y - 30))


def draw_interface():
    pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, 92))
    pygame.draw.line(screen, GOLD, (0, 92), (WIDTH, 92), 1)
    draw_text("ODYSSEY", font_title, GOLD, (35, 18))
    draw_text("THE FRACTURED SEA", font_small, MUTED, (38, 63))
    draw_text("MODE: " + ("CHRONOS DEMO" if DEMO_MODE else "CINEMATIC"),
              font_small, MUTED, (365, 28))

    status = "REPLAY" if replay_mode else navigation_status()
    draw_text(f"CHRONOS ENGINE: {status}", font_small, GOLD, (840, 28))
    draw_text(f"SIMULATION TIME: {(replay_time if replay_mode else simulation_time):06.1f}",
              font_small, WHITE, (840, 54))
    remaining = max(0, len(path) - navigator.index - 1) if path else 0
    draw_text(f"ROUTE STEPS REMAINING: {remaining}",
              font_small, MUTED, (570, 54))

    if path:
        draw_text(f"ETA: {route_duration}s   STORM EXPOSURE: {route_exposure:.2f}",
                  font_small, MUTED, (35, 115))

    if status == "WAITING":
        draw_text("POSEIDON BLOCKS THE PASSAGE — HOLD POSITION",
                  font_small, DANGER, (325, 135))
    elif status == "ARRIVED":
        draw_text("MISSION COMPLETE — ITHACA REACHED",
                  font_normal, GOLD, (375, 135))
    elif status == "NO ROUTE":
        draw_text("NO SAFE ROUTE — CHECK THE NAVIGATION MAP",
                  font_small, DANGER, (340, 135))

    pygame.draw.rect(screen, PANEL, (0, HEIGHT - 70, WIDTH, 70))
    pygame.draw.line(screen, GOLD, (0, HEIGHT - 70), (WIDTH, HEIGHT - 70), 1)
    draw_text("SPACE: PLAY  R: RESET", font_small, WHITE, (25, HEIGHT - 42))
    draw_text("1: SEA  2: DEMO", font_small, WHITE, (245, HEIGHT - 42))
    draw_text("3: SAFE  4: BAL  5: FAST", font_small, GOLD, (405, HEIGHT - 42))
    label, countdown = storm_countdown(replay_time if replay_mode else simulation_time)
    draw_text(f"{label}: {countdown:.1f}s", font_small,
              DANGER if storm_active(replay_time if replay_mode else simulation_time) else SAFE,
              (590, HEIGHT - 42))
    draw_text("T: REPLAY  C: COMPARE", font_small, GOLD, (985, HEIGHT - 42))

running = True

while running:
    dt = clock.tick(FPS) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_c:
                comparison_mode = not comparison_mode
            elif event.key == pygame.K_t and path:
                if not replay_mode:
                    replay_mode = True
                    replay_time = timeline.clamp(simulation_time)
                    paused = True
                else:
                    replay_mode = False
                    ship.update(get_ship_position(simulation_time))
            elif replay_mode and event.key in (pygame.K_LEFT, pygame.K_RIGHT,
                                                pygame.K_HOME, pygame.K_END):
                if event.key == pygame.K_HOME:
                    replay_time = timeline.start
                elif event.key == pygame.K_END:
                    replay_time = timeline.end
                else:
                    replay_time = timeline.clamp(replay_time + (
                        -1 if event.key == pygame.K_LEFT else 1))
            elif event.key == pygame.K_SPACE and not replay_mode and path and not navigator.finished:
                paused = not paused
            elif event.key in (pygame.K_1, pygame.K_2):
                selected_demo = event.key == pygame.K_2
                if DEMO_MODE != selected_demo:
                    DEMO_MODE = selected_demo
                    build_world()
            elif event.key in (pygame.K_3, pygame.K_4, pygame.K_5):
                selected = {
                    pygame.K_3: "survival",
                    pygame.K_4: "balanced",
                    pygame.K_5: "speed",
                }[event.key]
                if STRATEGY != selected:
                    STRATEGY = selected
                    build_world()
            elif event.key == pygame.K_r:
                simulation_time = 0.0
                paused = True
                navigator.reset()
                narrative.reset()
                ship.update(grid_to_world(*START))

    if not paused and not replay_mode and path:
        simulation_time += dt
        navigator.update(simulation_time)
        ship.update(get_ship_position(simulation_time))
        if navigator.finished:
            paused = True
            ship.update(grid_to_world(*GOAL))

    # Story reacts to the actual ship position and navigation state.
    if path and not replay_mode:
        storm_center = grid_to_world(*hazards[0]["position"])
        storm_distance = ship.distance_to(storm_center) / CELL_SIZE
        narrative.update(navigation_status(), storm_distance,
                         storm_active(simulation_time))

    displayed_time = replay_time if replay_mode else simulation_time
    if replay_mode:
        frame = timeline.frame(replay_time)
        if frame:
            ship.update(grid_to_world(*frame.position))
    draw_ocean(displayed_time)
    draw_islands()
    if comparison_mode:
        draw_comparison_routes()
    else:
        draw_navigation_path()
    draw_ithaca()
    draw_anomaly(displayed_time)
    draw_ship(displayed_time)
    if not replay_mode:
        draw_narrative()
    draw_timeline()
    draw_interface()
    if comparison_mode:
        draw_comparison_panel()
    pygame.display.flip()

pygame.quit()