from core.island_survival import IslandSurvival, DAY_SECONDS
from core.survival import ShipSurvival


def test_rest_every_two_days():
    game = IslandSurvival(5)
    assert not game.rest_due(2 * DAY_SECONDS - .1)
    assert game.rest_due(2 * DAY_SECONDS)


def test_island_loot_deterministic():
    a = IslandSurvival(5, seed=42)
    b = IslandSurvival(5, seed=42)
    assert a.dock(0, 0) and b.dock(0, 0)
    assert (a.wood, a.rope, a.food) == (b.wood, b.rope, b.food)


def test_no_repeat_looting_same_day():
    game = IslandSurvival(5)
    assert game.dock(1, 0)
    assert not game.dock(1, 1)
    assert game.dock(1, DAY_SECONDS)


def test_docking_invalid_island():
    assert not IslandSurvival(5).dock(9, 0)


def test_repair_requires_items():
    game = IslandSurvival(5)
    hull = ShipSurvival()
    hull.hull = 50
    assert not game.repair(hull)
    assert hull.hull == 50
    game.wood, game.rope = 3, 1
    assert game.repair(hull)
    assert hull.hull == 80
    assert (game.wood, game.rope) == (1, 0)


def test_rest_consumes_rations():
    game = IslandSurvival(5)
    assert game.rest(2 * DAY_SECONDS)
    assert game.food == 2
    assert game.last_rest_day == 2


def test_starving_crew_loses_morale():
    game = IslandSurvival(5)
    game.food = 0
    assert not game.rest(2 * DAY_SECONDS)
    assert game.morale == 75


def test_docking_restores_crew_when_due():
    game = IslandSurvival(5)
    assert game.dock(0, 2 * DAY_SECONDS)
    assert game.last_rest_day == 2
