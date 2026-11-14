
from core.navigator import Navigator


def test_ship_follows_path():
    path = [
        (0, 0, 0),
        (1, 0, 1),
        (2, 0, 2),
        (3, 0, 3),
    ]

    navigator = Navigator(path)

    assert navigator.position == (0, 0)

    navigator.update(1)
    assert navigator.position == (1, 0)

    navigator.update(2)
    assert navigator.position == (2, 0)

    navigator.update(3)
    assert navigator.position == (3, 0)
    assert navigator.finished


def test_ship_waits():
    path = [
        (0, 0, 0),
        (0, 0, 1),
        (1, 0, 2),
    ]

    navigator = Navigator(path)

    navigator.update(1)

    assert navigator.position == (0, 0)
    assert navigator.index == 1

    navigator.update(2)

    assert navigator.position == (1, 0)


def test_reset():
    path = [
        (0, 0, 0),
        (1, 0, 1),
    ]

    navigator = Navigator(path)

    navigator.update(1)
    assert navigator.finished

    navigator.reset()

    assert navigator.position == (0, 0)
    assert navigator.index == 0
    assert not navigator.finished
