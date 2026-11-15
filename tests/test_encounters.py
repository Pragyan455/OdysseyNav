from core.encounters import EncounterEngine, ENCOUNTERS
from core.island_survival import IslandSurvival
from core.survival import ShipSurvival


def setup():
    return EncounterEngine(), IslandSurvival(8), ShipSurvival()


def test_eight_unique_encounters():
    assert len(ENCOUNTERS) == 8
    assert len({e.title for e in ENCOUNTERS}) == 8


def test_circe_potion_changes_medicine_and_morale():
    engine, crew, ship = setup()
    assert engine.resolve(1, 0, crew, ship)[0]
    assert crew.medicine == 2 and crew.morale == 88


def test_sirens_damage_hull():
    engine, crew, ship = setup()
    assert engine.resolve(2, 0, crew, ship)[0]
    assert ship.hull == 78 and crew.food == 7


def test_unaffordable_choice_does_not_consume_encounter():
    engine, crew, ship = setup()
    assert not engine.resolve(2, 1, crew, ship)[0]
    assert engine.available(2)


def test_merchant_trade_costs_rations():
    engine, crew, ship = setup()
    assert engine.resolve(5, 0, crew, ship)[0]
    assert (crew.food, crew.wood, crew.rope) == (2, 3, 2)


def test_encounter_cannot_repeat():
    engine, crew, ship = setup()
    assert engine.resolve(4, 1, crew, ship)[0]
    assert not engine.resolve(4, 1, crew, ship)[0]
    assert crew.food == 7


def test_calypso_repair_requires_wood_and_damage():
    engine, crew, ship = setup()
    ship.hull = 60
    assert engine.resolve(7, 0, crew, ship)[0]
    assert ship.hull == 80 and crew.wood == 0


def test_invalid_island_or_choice():
    engine, crew, ship = setup()
    assert not engine.resolve(8, 0, crew, ship)[0]
    assert not engine.resolve(0, 3, crew, ship)[0]


def test_morale_is_clamped():
    engine, crew, ship = setup()
    crew.morale = 98
    assert engine.resolve(3, 1, crew, ship)[0]
    assert crew.morale == 100


def test_history_records_decisions():
    engine, crew, ship = setup()
    assert engine.resolve(6, 1, crew, ship)[0]
    assert len(engine.history) == 1
    assert engine.history[0][:2] == (6, 1)
