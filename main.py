import math
import pygame

from core.strategy import StrategyPlanner
from core.navigator import Navigator
from core.narrative import NarrativeEngine
from core.timeline import VoyageTimeline
from core.comparison import compare_strategies
from core.oracle import analyze_strategies
from core.title_scene import CinematicSea
from core.manual_control import ManualShip
from core.survival import ShipSurvival
from core.island_survival import IslandSurvival, DAY_SECONDS
from core.encounters import EncounterEngine

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

# Additional explorable islands. Centers are kept clear of Troy and Ithaca.
islands = [
    (360, 250, 55), (580, 440, 65), (790, 260, 60),
    (245, 530, 42), (470, 160, 38), (930, 515, 48),
    (1020, 220, 36), (720, 570, 38),
]
ISLAND_NAMES = ["Aeolia", "Circe's Isle", "The Sirens", "Thrinacia",
                "Ogygia", "Phaeacia", "Lotus Shore", "Calypso's Haven"]


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
    global comparison_results, comparison_mode, oracle_verdict, oracle_mode
    global manual_mode, manual_ship, manual_arrived, survival, defeat
    global island_game, voyage_target, pending_dock, crew_warning
    global encounters, encounter_island, encounter_message

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
    oracle_verdict = analyze_strategies(comparison_results)
    path = list(comparison_results[STRATEGY].path) or None
    route_duration = path[-1][2] - path[0][2] if path else None
    route_exposure = (
        sum(planner.risk_at(x, y, t, hazards) for x, y, t in path[1:])
        if path else None
    )
    navigator = Navigator(path)
    ship = grid_to_world(*START)
    manual_ship = ManualShip(ship.x, ship.y)
    manual_mode = False
    manual_arrived = False
    survival = ShipSurvival(repairs=0)
    island_game = IslandSurvival(len(islands))
    encounters = EncounterEngine()
    encounter_island = None
    encounter_message = ""
    voyage_target = GOAL
    pending_dock = None
    crew_warning = False
    defeat = False
    ithaca = grid_to_world(*GOAL)
    simulation_time = 0.0
    paused = True
    narrative = NarrativeEngine()
    timeline = VoyageTimeline(path, hazards)
    replay_mode = False
    replay_time = 0.0
    comparison_mode = False
    oracle_mode = False

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
    if defeat:
        return "SUNK"
    if manual_mode:
        return "ARRIVED" if manual_arrived else ("PAUSED" if paused else "MANUAL")
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

    for index, (x, y, radius) in enumerate(islands):
        pygame.draw.circle(screen, (25, 43, 53), (x, y), radius + 9)
        pygame.draw.circle(screen, ISLAND, (x, y), radius)
        pygame.draw.circle(screen, GOLD, (x, y), radius, 1)
        draw_text(ISLAND_NAMES[index], font_small, GOLD, (x - radius, y - radius - 20))
        if index in island_game.visited:
            pygame.draw.circle(screen, SAFE, (x, y), 6)


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



def draw_oracle_panel():
    """Show evidence-based mission conclusions from the same route comparison."""
    panel = pygame.Rect(235, 282, 730, 340)
    pygame.draw.rect(screen, PANEL, panel, border_radius=8)
    pygame.draw.rect(screen, GOLD, panel, 1, border_radius=8)
    draw_text("THE ORACLE'S VERDICT  |  V: CLOSE", font_normal, GOLD,
              (panel.x + 24, panel.y + 16))
    draw_text("STRATEGY       TRAVEL       WAITS       EXPOSURE", font_small,
              MUTED, (panel.x + 24, panel.y + 57))
    for index, strategy in enumerate(("survival", "balanced", "speed")):
        result = comparison_results[strategy]
        y = panel.y + 86 + index * 34
        if result.reachable:
            stats = (f"{result.travel_time:>5.0f}s"
                     f"          {result.waiting_steps:>3}"
                     f"          {result.storm_exposure:>7.2f}")
        else:
            stats = "NO SAFE ROUTE"
        draw_text(strategy.upper(), font_small, STRATEGY_COLORS[strategy],
                  (panel.x + 24, y))
        draw_text(stats, font_small, WHITE, (panel.x + 185, y))

    def names(values):
        return ", ".join(name.title() for name in values) if values else "None"

    draw_text("FASTEST: " + names(oracle_verdict.fastest), font_small, GOLD,
              (panel.x + 24, panel.y + 202))
    draw_text("LOWEST EXPOSURE: " + names(oracle_verdict.safest), font_small,
              SAFE, (panel.x + 24, panel.y + 226))
    draw_text("NONDOMINATED: " + names(oracle_verdict.pareto_optimal),
              font_small, WHITE, (panel.x + 24, panel.y + 250))
    draw_text(oracle_verdict.summary, font_small, WHITE,
              (panel.x + 24, panel.y + 282))
    draw_text("Exposure is a relative score, not a probability.", font_small,
              MUTED, (panel.x + 24, panel.y + 308))


def draw_ship(t):
    x, y = ship.x, ship.y + math.sin(t * 2) * 3
    hull = [(-24, -12), (28, 0), (-24, 12), (-12, 0)]
    if manual_mode:
        angle = math.radians(manual_ship.heading)
        c, sn = math.cos(angle), math.sin(angle)
        hull = [(x + px * c - py * sn, y + px * sn + py * c)
                for px, py in hull]
        mast_a = (x - 4 * c + 18 * sn, y - 4 * sn - 18 * c)
        mast_b = (x - 4 * c - 18 * sn, y - 4 * sn + 18 * c)
    else:
        hull = [(x + px, y + py) for px, py in hull]
        mast_a, mast_b = (x - 4, y - 18), (x - 4, y + 18)
    pygame.draw.polygon(screen, GOLD, hull)
    pygame.draw.line(screen, WHITE, mast_a, mast_b, 2)
    pygame.draw.circle(screen, GOLD, (int(x), int(y)), 30, 1)
    if manual_mode:
        angle = math.radians(manual_ship.heading)
        tip = (x + 38 * math.cos(angle), y + 38 * math.sin(angle))
        pygame.draw.line(screen, SAFE, (x, y), tip, 3)
        pygame.draw.circle(screen, SAFE, (round(tip[0]), round(tip[1])), 4)


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


def draw_encounter_panel():
    """Modal island dialogue; no gameplay time advances while choosing."""
    if encounter_island is None:
        return
    encounter = encounters.get(encounter_island)
    if encounter is None:
        return
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((2, 8, 16, 190))
    screen.blit(veil, (0, 0))
    rect = pygame.Rect(170, 160, 860, 400)
    pygame.draw.rect(screen, PANEL, rect, border_radius=10)
    pygame.draw.rect(screen, GOLD, rect, 2, border_radius=10)
    draw_text('THE TRIALS OF ODYSSEUS', font_small, MUTED, (205, 186))
    draw_text(encounter.title, font_title, GOLD, (205, 218))
    draw_text(encounter.story, font_normal, WHITE, (205, 290))
    for index, choice in enumerate(encounter.choices):
        y = 351 + index * 70
        pygame.draw.rect(screen, (20, 42, 53), (202, y, 796, 58), border_radius=5)
        draw_text(f'{index + 1}  {choice.label}', font_normal, GOLD, (220, y + 5))
        draw_text(choice.description, font_small, WHITE, (220, y + 34))
    draw_text('PRESS 1 OR 2 TO DECIDE  |  ESC: RETURN TO SEA', font_small, MUTED, (205, 535))
    if encounter_message:
        draw_text(encounter_message[:100], font_small, DANGER, (205, 322))


def draw_interface():
    pygame.draw.rect(screen, PANEL, (0, 0, WIDTH, 92))
    pygame.draw.line(screen, GOLD, (0, 92), (WIDTH, 92), 1)
    draw_text("ODYSSEY", font_title, GOLD, (35, 18))
    draw_text("THE FRACTURED SEA", font_small, MUTED, (38, 63))
    draw_text("MODE: " + ("CHRONOS DEMO" if DEMO_MODE else "CINEMATIC"),
              font_small, MUTED, (365, 28))

    status = "REPLAY" if replay_mode else navigation_status()
    draw_text("CONTROL: " + ("MANUAL" if manual_mode else "CHRONOS AI"),
              font_small, SAFE if manual_mode else GOLD, (365, 54))
    draw_text(f"CHRONOS ENGINE: {status}", font_small, GOLD, (840, 28))
    draw_text(f"SIMULATION TIME: {(replay_time if replay_mode else simulation_time):06.1f}",
              font_small, WHITE, (840, 54))
    remaining = max(0, len(path) - navigator.index - 1) if path else 0
    draw_text(f"ROUTE STEPS REMAINING: {remaining}",
              font_small, MUTED, (570, 54))

    hull_color = SAFE if survival.hull > 60 else (GOLD if survival.hull > 30 else DANGER)
    draw_text(f"HULL: {survival.hull:3d}%   STORM HITS: {survival.hits}",
              font_small, hull_color, (35, 95))
    draw_text(f"DAY {island_game.day(simulation_time)+1}  |  FOOD {island_game.food}  WOOD {island_game.wood}  ROPE {island_game.rope}  MORALE {island_game.morale}%",
              font_small, GOLD, (365, 95))
    draw_text(island_game.message[:110], font_small, DANGER if crew_warning else SAFE, (35, 155))
    if path:
        draw_text(f"ETA: {route_duration}s   STORM EXPOSURE: {route_exposure:.2f}",
                  font_small, MUTED, (35, 115))

    if status == "SUNK":
        draw_text("YOUR SHIP HAS SUNK — PRESS R TO RETRY",
                  font_normal, DANGER, (355, 135))
    elif status == "WAITING":
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
    draw_text("T: REPLAY  C: COMPARE  V: ORACLE", font_small, GOLD, (925, HEIGHT - 42))
    if manual_mode:
        draw_text(f"MANUAL | W/S THROTTLE  A/D RUDDER  M: AI  SPEED {manual_ship.speed:+.0f}",
                  font_small, SAFE, (35, HEIGHT - 96))
    else:
        draw_text("M: TAKE THE HELM", font_small, SAFE, (35, HEIGHT - 96))
    draw_text("E: REPAIR   F: DOCK   G: MEDICINE   CLICK: WAYPOINT", font_small, GOLD, (475, HEIGHT - 96))
    draw_text(f"TRIALS COMPLETED: {len(encounters.completed)}/8", font_small, GOLD, (840, 95))

# Original procedural cinematic opening; no reference photos or movie assets.
show_title = True
title_elapsed = 0.0
TITLE_BUTTON = pygame.Rect(WIDTH // 2 - 184, 538, 368, 65)
font_hero = pygame.font.SysFont("timesnewroman", 118)
font_subtitle = pygame.font.SysFont("georgia", 22)
font_kicker = pygame.font.SysFont("consolas", 13)
font_eyebrow = pygame.font.SysFont("georgia", 15)
TITLE_SCENE = CinematicSea(WIDTH, HEIGHT)


def draw_title_screen(t):
    """Animated, wholly original ocean scene and interactive voyage button."""
    TITLE_SCENE.draw(screen, t)

    center = WIDTH // 2
    kicker = font_kicker.render("A VOYAGE BEYOND THE REACH OF TIME", True,
                                (182, 184, 178))
    screen.blit(kicker, kicker.get_rect(center=(center, 155)))

    # A soft shadow ensures the title remains readable over the photograph.
    title_shadow = font_hero.render("ODYSSEY", True, (0, 5, 10))
    screen.blit(title_shadow, title_shadow.get_rect(center=(center + 3, 257)))
    title = font_hero.render("ODYSSEY", True, (232, 218, 185))
    screen.blit(title, title.get_rect(center=(center, 253)))

    pygame.draw.line(screen, (182, 154, 109), (center - 165, 327),
                     (center + 165, 327), 1)
    subtitle = font_subtitle.render("T H E   F R A C T U R E D   S E A", True,
                                    (218, 211, 194))
    screen.blit(subtitle, subtitle.get_rect(center=(center, 370)))
    tagline = font_eyebrow.render("THE SEA REMEMBERS. TIME DOES NOT.", True,
                                  (188, 198, 198))
    screen.blit(tagline, tagline.get_rect(center=(center, 417)))

    hovered = TITLE_BUTTON.collidepoint(pygame.mouse.get_pos())
    pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND if hovered
                            else pygame.SYSTEM_CURSOR_ARROW)
    button_layer = pygame.Surface(TITLE_BUTTON.size, pygame.SRCALPHA)
    button_layer.fill((13, 21, 27, 225 if hovered else 195))
    screen.blit(button_layer, TITLE_BUTTON.topleft)
    pygame.draw.rect(screen, (245, 218, 162) if hovered else (178, 155, 115),
                     TITLE_BUTTON, 2 if hovered else 1)
    if hovered:
        pygame.draw.line(screen, (246, 220, 174),
                         (TITLE_BUTTON.x + 15, TITLE_BUTTON.bottom + 6),
                         (TITLE_BUTTON.right - 15, TITLE_BUTTON.bottom + 6), 2)
    label = font_subtitle.render("B E G I N   V O Y A G E", True,
                                 (255, 238, 201) if hovered else (226, 208, 175))
    screen.blit(label, label.get_rect(center=TITLE_BUTTON.center))
    hint = font_kicker.render("PRESS ENTER OR CLICK TO SET SAIL", True,
                              (177, 184, 183))
    screen.blit(hint, hint.get_rect(center=(center, 631)))
    footer = font_kicker.render("CHRONOS  /  THE COUNCIL OF FATES  /  THE ORACLE", True,
                                (158, 169, 169))
    screen.blit(footer, footer.get_rect(center=(center, HEIGHT - 31)))


def begin_voyage():
    global show_title
    show_title = False


def ship_cell():
    gx = max(0, min(GRID_WIDTH - 1, int(ship.x // CELL_SIZE)))
    gy = max(0, min(GRID_HEIGHT - 1, int(ship.y // CELL_SIZE)))
    return gx, gy


def blocked_at(px, py):
    return (int(px // CELL_SIZE), int(py // CELL_SIZE)) in obstacles


def nearby_island():
    """Return island index only when the ship is alongside its shore."""
    if DEMO_MODE:
        return None
    for index, (x, y, radius) in enumerate(islands):
        distance = ship.distance_to((x, y))
        if radius + 15 <= distance <= radius + 62:
            return index
    return None


def nearest_dock():
    """Find a traversable shoreline grid cell for the nearest island."""
    candidates = []
    for index, (ix, iy, radius) in enumerate(islands):
        for gx in range(1, GRID_WIDTH - 1):
            for gy in range(4, GRID_HEIGHT - 4):
                if (gx, gy) in obstacles:
                    continue
                center = grid_to_world(gx, gy)
                distance = center.distance_to((ix, iy))
                if radius + 20 <= distance <= radius + 48:
                    candidates.append((ship.distance_to(center), index, (gx, gy)))
    candidates.sort(key=lambda item: item[0])
    return candidates[:30]


def set_waypoint(target):
    """Replan without teleporting or resetting the simulation clock."""
    global path, navigator, timeline, route_duration, route_exposure, voyage_target, paused
    if target in obstacles or not (0 <= target[0] < GRID_WIDTH and 0 <= target[1] < GRID_HEIGHT):
        island_game.message = 'Cannot sail onto land. Choose open water.'
        return False
    new_path = planner.plan_strategy(ship_cell(), target, hazards=hazards,
                    strategy=STRATEGY, start_time=int(simulation_time),
                    max_time=int(simulation_time) + 160)
    if not new_path:
        island_game.message = 'Chronos cannot find a safe route there.'
        return False
    path = new_path
    navigator = Navigator(path)
    timeline = VoyageTimeline(path, hazards)
    route_duration = path[-1][2] - path[0][2]
    route_exposure = sum(planner.risk_at(x,y,t,hazards) for x,y,t in path[1:])
    voyage_target = target
    paused = False
    return True


def toggle_helm():
    """Hand control to the player, or replan from the player's current position."""
    global manual_mode, manual_ship, path, navigator, timeline, paused
    global route_duration, route_exposure, replay_mode, manual_arrived
    if replay_mode or defeat:
        return
    if not manual_mode:
        manual_ship = ManualShip(ship.x, ship.y)
        manual_mode = True
        manual_arrived = False
        paused = True  # player presses SPACE to start sailing
        return
    # Resume AI from the current location and the current storm phase.
    new_path = planner.plan_strategy(
        ship_cell(), voyage_target, hazards=hazards, strategy=STRATEGY,
        start_time=int(simulation_time), max_time=int(simulation_time) + 150
    )
    if not new_path:
        print("Chronos: cannot find a safe route from this position; remain in manual mode")
        return
    path = new_path
    navigator = Navigator(path)
    timeline = VoyageTimeline(path, hazards)
    route_duration = path[-1][2] - path[0][2]
    route_exposure = sum(planner.risk_at(x, y, t, hazards) for x, y, t in path[1:])
    manual_mode = False
    paused = True


running = True

while running:
    dt = clock.tick(FPS) / 1000.0
    if show_title:
        title_elapsed += dt
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif show_title:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if TITLE_BUTTON.collidepoint(event.pos):
                    begin_voyage()
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                begin_voyage()
        elif encounter_island is not None:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    encounter_island = None
                    encounter_message = ''
                elif event.key in (pygame.K_1, pygame.K_2):
                    decision = 0 if event.key == pygame.K_1 else 1
                    success, outcome = encounters.resolve(encounter_island, decision, island_game, survival)
                    if success:
                        island_id = encounter_island
                        encounter_island = None
                        encounter_message = ''
                        island_game.dock(island_id, simulation_time)
                        island_game.message = outcome + ' ' + island_game.message
                        crew_warning = island_game.rest_due(simulation_time)
                        paused = True
                        manual_ship.speed = 0
                        pending_dock = None
                        if survival.sunk or island_game.failed:
                            defeat = True
                        print(island_game.message)
                    else:
                        encounter_message = outcome
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not replay_mode and not defeat:
            if 175 < event.pos[1] < HEIGHT - 115 and not DEMO_MODE:
                waypoint = (int(event.pos[0] // CELL_SIZE), int(event.pos[1] // CELL_SIZE))
                if manual_mode:
                    island_game.message = 'Switch to Chronos AI (M) to set waypoints.'
                elif set_waypoint(waypoint):
                    island_game.message = 'Chronos sailing toward selected waypoint.'
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                show_title = True
                paused = True
                replay_mode = False
                comparison_mode = False
                oracle_mode = False
            elif event.key == pygame.K_e and not replay_mode and not defeat:
                island_game.repair(survival)
            elif event.key == pygame.K_g and not replay_mode and not defeat:
                if island_game.medicine and island_game.morale < 100:
                    island_game.medicine -= 1
                    island_game.morale = min(100, island_game.morale + 30)
                    island_game.message = 'Medicine restored 30 crew morale.'
                else:
                    island_game.message = 'No medicine available, or morale already full.'
            elif event.key == pygame.K_f and not replay_mode and not defeat:
                dock_id = nearby_island()
                if dock_id is None:
                    island_game.message = 'Approach an island shoreline to dock (F).'
                else:
                    if island_game.last_visit_day.get(dock_id) == island_game.day(simulation_time):
                        island_game.message = 'Island already searched today. Return tomorrow.'
                    elif encounters.available(dock_id):
                        encounter_island = dock_id
                        encounter_message = ''
                        paused = True
                        manual_ship.speed = 0
                    else:
                        island_game.dock(dock_id, simulation_time)
                        crew_warning = island_game.rest_due(simulation_time)
                        paused = True
                        manual_ship.speed = 0
                        pending_dock = None
                        print(island_game.message)
            elif event.key == pygame.K_m:
                toggle_helm()
            elif event.key == pygame.K_v:
                oracle_mode = not oracle_mode
                if oracle_mode:
                    comparison_mode = False
            elif event.key == pygame.K_c:
                comparison_mode = not comparison_mode
                if comparison_mode:
                    oracle_mode = False
            elif event.key == pygame.K_t and path and not manual_mode:
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
            elif event.key == pygame.K_SPACE and not defeat and not replay_mode and (manual_mode or (path and not navigator.finished)):
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
                build_world()

    if show_title:
        draw_title_screen(title_elapsed)
        pygame.display.flip()
        continue

    # A two-day voyage requires a mandatory island stop. Chronos diverts
    # automatically; manual captains receive a warning and must find a shore.
    if not DEMO_MODE and not replay_mode and not defeat:
        crew_warning = island_game.rest_due(simulation_time)
        if crew_warning and not manual_mode and pending_dock is None and not paused:
            for _, island_id, dock_cell in nearest_dock():
                if set_waypoint(dock_cell):
                    pending_dock = island_id
                    island_game.message = f'CREW REST REQUIRED: heading to {ISLAND_NAMES[island_id]}. Press F at shore.'
                    break
        if pending_dock is not None and nearby_island() == pending_dock:
            paused = True
            island_game.message = f'ARRIVED AT {ISLAND_NAMES[pending_dock]}: press F to land and resupply.'
            pending_dock = None

    if manual_mode and not paused and not replay_mode:
        simulation_time += dt
        keys = pygame.key.get_pressed()
        throttle = int(keys[pygame.K_w] or keys[pygame.K_UP]) - int(keys[pygame.K_s] or keys[pygame.K_DOWN])
        rudder = int(keys[pygame.K_d] or keys[pygame.K_RIGHT]) - int(keys[pygame.K_a] or keys[pygame.K_LEFT])
        manual_ship.step(dt, throttle, rudder, blocked_at, WIDTH, HEIGHT)
        ship.update(manual_ship.x, manual_ship.y)
        if ship.distance_to(ithaca) < CELL_SIZE * 0.7 and not island_game.rest_due(simulation_time):
            manual_arrived = True
            paused = True
            manual_ship.speed = 0
    elif not manual_mode and not paused and not replay_mode and path:
        simulation_time += dt
        navigator.update(simulation_time)
        ship.update(get_ship_position(simulation_time))
        if navigator.finished:
            paused = True
            ship.update(grid_to_world(*voyage_target))
            if voyage_target != GOAL:
                island_game.message = 'Waypoint reached. Press F if alongside an island, or click another destination.' 

    # Starving sailors lose morale if a captain ignores the required stop.
    if island_game.failed:
        defeat = True
        paused = True
    # Storm damage is based on the vessel's actual position, not the route preview.
    if not paused and not replay_mode and not defeat:
        if survival.update(ship.x / CELL_SIZE, ship.y / CELL_SIZE,
                           simulation_time, hazards):
            print(f"POSEIDON STRIKES! Hull integrity: {survival.hull}%")
        if survival.sunk:
            defeat = True
            paused = True
            manual_ship.speed = 0.0

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
    if oracle_mode:
        draw_oracle_panel()
    draw_encounter_panel()
    pygame.display.flip()

pygame.quit()