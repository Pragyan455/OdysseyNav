
import math
import pygame

pygame.init()

WIDTH, HEIGHT = 1200, 750
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ODYSSEY | The Fractured Sea")
clock = pygame.time.Clock()

# Colors
OCEAN = (8, 22, 38)
GOLD = (218, 175, 104)
WHITE = (230, 224, 210)
MUTED = (120, 145, 160)
ISLAND = (63, 83, 91)
DANGER = (175, 65, 70)

font_title = pygame.font.SysFont("georgia", 34)
font_normal = pygame.font.SysFont("georgia", 18)
font_small = pygame.font.SysFont("consolas", 14)

# Navigation world
ship = pygame.Vector2(130, 380)
ithaca = pygame.Vector2(1040, 380)

islands = [
    (360, 250, 65),
    (580, 440, 85),
    (790, 260, 75),
]

running = True
paused = True
simulation_time = 0.0


def draw_text(text, font, color, position):
    surface = font.render(text, True, color)
    screen.blit(surface, position)


def draw_ocean(t):
    screen.fill(OCEAN)

    # Subtle animated ocean lines
    for y in range(110, HEIGHT - 70, 32):
        for x in range(0, WIDTH, 95):
            offset = math.sin(t * 0.8 + x * 0.02 + y * 0.01) * 8
            pygame.draw.line(
                screen,
                (17, 42, 59),
                (x + offset, y),
                (x + 48 + offset, y),
                1,
            )


def draw_islands():
    for x, y, radius in islands:
        pygame.draw.circle(screen, (25, 43, 53), (x, y), radius + 9)
        pygame.draw.circle(screen, ISLAND, (x, y), radius)
        pygame.draw.circle(screen, GOLD, (x, y), radius, 1)


def draw_ship(t):
    x = ship.x
    y = ship.y + math.sin(t * 2) * 3

    # Hull
    points = [
        (x - 24, y - 12),
        (x + 28, y),
        (x - 24, y + 12),
        (x - 12, y),
    ]

    pygame.draw.polygon(screen, GOLD, points)

    # Mast
    pygame.draw.line(
        screen, WHITE,
        (x - 4, y - 18),
        (x - 4, y + 18),
        2,
    )

    pygame.draw.circle(screen, GOLD, (int(x), int(y)), 30, 1)


def draw_ithaca():
    x, y = int(ithaca.x), int(ithaca.y)

    pygame.draw.circle(screen, GOLD, (x, y), 36, 2)
    pygame.draw.circle(screen, GOLD, (x, y), 6)

    draw_text("ITHACA", font_normal, GOLD, (x - 35, y + 48))


def draw_anomaly(t):
    x, y = 670, 260
    radius = 43 + math.sin(t * 2) * 6

    pygame.draw.circle(
        screen, DANGER, (x, y), int(radius), 2
    )

    pygame.draw.circle(
        screen, (95, 40, 55), (x, y), 23
    )

    draw_text(
        "TEMPORAL ANOMALY",
        font_small,
        DANGER,
        (x - 80, y - 75),
    )


def draw_interface():
    pygame.draw.rect(screen, (5, 15, 27), (0, 0, WIDTH, 92))
    pygame.draw.line(screen, GOLD, (0, 92), (WIDTH, 92), 1)

    draw_text(
        "ODYSSEY",
        font_title,
        GOLD,
        (35, 18),
    )

    draw_text(
        "THE FRACTURED SEA",
        font_small,
        MUTED,
        (38, 63),
    )

    status = "PAUSED" if paused else "ACTIVE"

    draw_text(
        f"CHRONOS ENGINE: {status}",
        font_small,
        GOLD,
        (840, 28),
    )

    draw_text(
        f"SIMULATION TIME: {simulation_time:06.1f}",
        font_small,
        WHITE,
        (840, 54),
    )

    pygame.draw.rect(
        screen,
        (5, 15, 27),
        (0, HEIGHT - 70, WIDTH, 70),
    )

    pygame.draw.line(
        screen,
        GOLD,
        (0, HEIGHT - 70),
        (WIDTH, HEIGHT - 70),
        1,
    )

    draw_text(
        "SPACE: START / PAUSE",
        font_small,
        WHITE,
        (35, HEIGHT - 42),
    )

    draw_text(
        "R: RESET",
        font_small,
        WHITE,
        (300, HEIGHT - 42),
    )

    draw_text(
        "DESTINATION: ITHACA",
        font_small,
        GOLD,
        (850, HEIGHT - 42),
    )


while running:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused

            elif event.key == pygame.K_r:
                simulation_time = 0.0
                paused = True

    if not paused:
        simulation_time += dt

    draw_ocean(simulation_time)
    draw_islands()
    draw_ithaca()
    draw_anomaly(simulation_time)
    draw_ship(simulation_time)
    draw_interface()

    pygame.display.flip()

pygame.quit()
