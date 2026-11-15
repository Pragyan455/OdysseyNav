from core.narrative import NarrativeEngine


def test_departure_only_once():
    engine = NarrativeEngine()
    assert engine.update("SAILING").key == "departure"
    assert engine.update("SAILING") is None


def test_storm_encounter_and_wait():
    engine = NarrativeEngine()
    engine.update("SAILING")
    assert engine.update("SAILING", distance_to_storm=3, storm_active=True).key == "approach"
    assert engine.update("WAITING", distance_to_storm=2, storm_active=True).key == "waiting"
    assert engine.update("WAITING", distance_to_storm=2, storm_active=True) is None


def test_escape_after_encounter():
    engine = NarrativeEngine()
    engine.update("SAILING")
    engine.update("SAILING", distance_to_storm=2, storm_active=True)
    assert engine.update("SAILING", distance_to_storm=8, storm_active=True).key == "escape"
    assert engine.update("SAILING", distance_to_storm=9, storm_active=True) is None


def test_arrival_and_reset():
    engine = NarrativeEngine()
    assert engine.update("ARRIVED").key == "arrival"
    assert engine.update("ARRIVED") is None
    engine.reset()
    assert engine.update("SAILING").key == "departure"


def test_paused_does_not_start_story():
    engine = NarrativeEngine()
    assert engine.update("PAUSED") is None
    assert engine.current is None
