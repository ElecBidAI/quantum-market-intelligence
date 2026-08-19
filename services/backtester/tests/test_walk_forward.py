import pytest

from backtester.walk_forward import walk_forward_windows


def test_walk_forward_windows_known_value():
    bars = list(range(10))
    windows = walk_forward_windows(bars, train_size=4, test_size=2, step=2)
    assert windows == [
        ([0, 1, 2, 3], [4, 5]),
        ([2, 3, 4, 5], [6, 7]),
        ([4, 5, 6, 7], [8, 9]),
    ]


def test_walk_forward_windows_defaults_step_to_test_size():
    bars = list(range(10))
    with_default_step = walk_forward_windows(bars, train_size=4, test_size=2)
    explicit_step = walk_forward_windows(bars, train_size=4, test_size=2, step=2)
    assert with_default_step == explicit_step


def test_walk_forward_windows_non_overlapping_test_when_step_equals_train_plus_test():
    bars = list(range(12))
    windows = walk_forward_windows(bars, train_size=4, test_size=2, step=6)
    assert windows == [([0, 1, 2, 3], [4, 5]), ([6, 7, 8, 9], [10, 11])]


def test_walk_forward_windows_empty_when_not_enough_bars():
    bars = list(range(3))
    assert walk_forward_windows(bars, train_size=4, test_size=2) == []


def test_walk_forward_windows_rejects_invalid_sizes():
    with pytest.raises(ValueError):
        walk_forward_windows([1, 2, 3], train_size=0, test_size=1)
    with pytest.raises(ValueError):
        walk_forward_windows([1, 2, 3], train_size=1, test_size=0)
    with pytest.raises(ValueError):
        walk_forward_windows([1, 2, 3], train_size=1, test_size=1, step=0)
