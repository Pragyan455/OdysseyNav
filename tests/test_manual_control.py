import math
from core.manual_control import ManualShip


def test_forward_acceleration():
    s = ManualShip(100, 100)
    for _ in range(30):
        s.step(1 / 60, 1, 0, lambda x, y: False, 1200, 750)
    assert s.x > 100 and s.y == 100 and s.speed > 0


def test_reverse():
    s = ManualShip(100, 100)
    for _ in range(30):
        s.step(1 / 60, -1, 0, lambda x, y: False, 1200, 750)
    assert s.x < 100 and s.speed < 0


def test_turning_changes_heading():
    s = ManualShip(100, 100, speed=40)
    s.step(.1, 0, 1, lambda x, y: False, 1200, 750)
    assert 0 < s.heading < 360 and s.y > 100


def test_collision_prevents_movement():
    s = ManualShip(100, 100, speed=80)
    assert not s.step(.1, 1, 0, lambda x, y: True, 1200, 750)
    assert (s.x, s.y, s.speed) == (100, 100, 0)


def test_boundary_prevents_movement():
    s = ManualShip(1199, 100, speed=90)
    assert not s.step(.1, 0, 0, lambda x, y: False, 1200, 750)
    assert s.x == 1199


def test_dt_is_clamped():
    s = ManualShip(100, 100)
    s.step(10, 1, 0, lambda x, y: False, 1200, 750)
    assert s.speed <= 6.5 + 1e-6
