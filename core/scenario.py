"""The two voyages (SEA and DEMO), as set up in main.py.

These values and rules are copied exactly from main.py so the 3D version
(main3d.py) sails the same routes. main.py does not import this file yet;
if you change the map in one place, change it in the other too.
"""

import math

WIDTH, HEIGHT = 1200, 750
CELL_SIZE = 25
GRID_WIDTH = WIDTH // CELL_SIZE      # 48
GRID_HEIGHT = HEIGHT // CELL_SIZE    # 30

START = (5, 15)
GOAL = (41, 15)

# DEMO mode: one straight channel ("THE NARROWS") through the middle
PASSAGE_Y = START[1]
PASSAGE_START = 10
PASSAGE_END = 37

# SEA mode: the original islands, in pixels (x, y, radius)
ISLANDS = [(360, 250, 65), (580, 440, 85), (790, 260, 75)]
ISLAND_MARGIN_PX = 20

# Seconds of simulation time per planner step (main.py compares the clock
# directly with each state's t)
STEP_SECONDS = 1.0
MAX_TIME = 150


def grid_to_pixel(x, y):
    return (x * CELL_SIZE + CELL_SIZE / 2, y * CELL_SIZE + CELL_SIZE / 2)


def create_obstacles(demo):
    blocked = set()
    if demo:
        for gx in range(PASSAGE_START, PASSAGE_END + 1):
            for gy in range(GRID_HEIGHT):
                if gy != PASSAGE_Y:
                    blocked.add((gx, gy))
        return blocked

    for gx in range(GRID_WIDTH):
        for gy in range(GRID_HEIGHT):
            px, py = grid_to_pixel(gx, gy)
            for ix, iy, radius in ISLANDS:
                if math.hypot(px - ix, py - iy) < radius + ISLAND_MARGIN_PX:
                    blocked.add((gx, gy))
                    break
    return blocked


def create_hazards(demo):
    if demo:
        # Single-cell storm in the channel: demonstrates waiting.
        return [{
            "position": (24, PASSAGE_Y),
            "radius": 0,
            "period": 12,
            "active_duration": 8,
        }]
    # Open sea, with a larger temporal anomaly.
    return [{
        "position": (670 // CELL_SIZE, 260 // CELL_SIZE),
        "radius": 2,
        "period": 12,
        "active_duration": 6,
    }]


def plan(planner_cls, demo):
    """Return (obstacles, hazards, path) for the chosen mode."""
    obstacles = create_obstacles(demo)
    hazards = create_hazards(demo)
    planner = planner_cls(GRID_WIDTH, GRID_HEIGHT, obstacles)
    path = planner.plan(START, GOAL, hazards=hazards,
                        start_time=0, max_time=MAX_TIME)
    return obstacles, hazards, path


def hazard_active(hazard, t):
    """Planner rule: is the hazard on at whole step t?"""
    return (t % hazard["period"]) < hazard["active_duration"]


def hazard_rise(hazard, sim_seconds):
    """0.0 (hidden) to 1.0 (fully up), for drawing the hazard smoothly.

    The planner checks a move from step t to t+1 against the hazard at t+1,
    so the picture during (t, t+1] shows the state at t+1. The hazard rises
    during the step before it turns on and sinks during the step after.
    """
    steps = sim_seconds / STEP_SECONDS
    shown = math.ceil(steps - 1e-9)
    frac = min(1.0, max(0.0, steps - (shown - 1)))
    now = hazard_active(hazard, shown)
    before = hazard_active(hazard, shown - 1)
    if now and not before:
        return frac
    if now:
        return 1.0
    if before:
        return 1.0 - frac
    return 0.0
