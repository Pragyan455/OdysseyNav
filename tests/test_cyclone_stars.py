
import random

from core import cyclone, starpuzzle


# --- cyclone ---------------------------------------------------------------

def test_cyclone_chases_at_half_speed():
    c = cyclone.Cyclone(0, 0)
    c.chase(10, 0, steps=4)                 # 4 steps * 0.5 cells/step
    assert (c.x, c.y) == (2.0, 0.0)
    c.chase(2.5, 0, steps=10)               # never overshoots the ship
    assert (c.x, c.y) == (2.5, 0.0)


def test_cyclone_hit_radius():
    c = cyclone.Cyclone(5, 5)
    assert c.hits(5.5, 5.3)
    assert not c.hits(6, 5.5)


# --- star puzzle -----------------------------------------------------------

def make_puzzle(seed=0):
    return starpuzzle.StarPuzzle(random.Random(seed))


def finish_show(p):
    p.update(starpuzzle.SHOW_SECONDS * p.length + starpuzzle.PAUSE_SECONDS)
    assert p.phase == "input"


def test_pattern_is_revealed_one_star_at_a_time():
    p = make_puzzle()
    assert p.revealed() == p.order[:1]
    p.update(starpuzzle.SHOW_SECONDS)
    assert p.revealed() == p.order[:2]


def test_clicks_ignored_while_showing():
    p = make_puzzle()
    assert p.click(*p.stars[p.order[0]]) is None


def test_correct_order_solves():
    p = make_puzzle()
    finish_show(p)
    results = [p.click(*p.stars[i]) for i in p.order]
    assert results == ["ok"] * (p.length - 1) + ["solved"]
    assert not p.done
    p.update(starpuzzle.SOLVED_SECONDS)
    assert p.done


def test_wrong_star_shifts_the_sky():
    p = make_puzzle()
    finish_show(p)
    old_stars = p.stars
    wrong = next(i for i in range(p.num_stars) if i != p.order[0])
    assert p.click(*p.stars[wrong]) == "wrong"
    p.update(starpuzzle.WRONG_SECONDS)
    assert p.phase == "show" and p.stars != old_stars


def test_click_on_empty_sky_is_ignored():
    p = make_puzzle()
    finish_show(p)
    assert p.click(5.0, 5.0) is None
    assert p.phase == "input"
