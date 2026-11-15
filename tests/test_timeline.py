from core.timeline import VoyageTimeline

PATH = [(0, 1, 0), (1, 1, 1), (1, 1, 2), (2, 1, 3)]
HAZARDS = [{'position': (1, 1), 'radius': 0, 'period': 4, 'active_duration': 2}]


def test_interpolation():
    timeline = VoyageTimeline(PATH, HAZARDS)
    assert timeline.frame(0.5).position == (0.5, 1.0)


def test_wait_detection():
    timeline = VoyageTimeline(PATH, HAZARDS)
    assert timeline.frame(1.5).waiting
    assert timeline.wait_times == [1.0]
    assert not timeline.frame(2.5).waiting


def test_storm_history():
    timeline = VoyageTimeline(PATH, HAZARDS)
    assert timeline.frame(1).storm_active
    assert not timeline.frame(2).storm_active


def test_bounds_and_arrival():
    timeline = VoyageTimeline(PATH, HAZARDS)
    assert timeline.frame(-100).time == 0
    assert timeline.frame(100).time == 3
    assert timeline.frame(100).arrived


def test_empty_route():
    timeline = VoyageTimeline(None, HAZARDS)
    assert timeline.frame(1) is None


def test_replay_does_not_mutate_route():
    path = PATH.copy()
    timeline = VoyageTimeline(path, HAZARDS)
    timeline.frame(2.5)
    assert path == PATH
