import pytest

from quant_core.transforms import (
    percentile,
    relative_volume,
    rolling_normalize,
    winsorize,
    z_score,
)


def test_z_score_known_value():
    assert z_score(110, mean=100, std_dev=10) == pytest.approx(1.0)


def test_z_score_rejects_non_positive_std_dev():
    with pytest.raises(ValueError):
        z_score(1, mean=0, std_dev=0)


def test_rolling_normalize_known_values():
    # window=2: for any 2-element window [a, b] with b > a, the population
    # std_dev is exactly (b - a) / 2, so the last point is always exactly
    # +1 std above the window mean.
    result = rolling_normalize([1, 2, 3, 4, 5], window=2)
    assert len(result) == 4
    for value in result:
        assert value == pytest.approx(1.0, rel=1e-9)


def test_rolling_normalize_rejects_short_series():
    with pytest.raises(ValueError):
        rolling_normalize([1, 2], window=3)


def test_rolling_normalize_rejects_zero_variance_window():
    with pytest.raises(ValueError):
        rolling_normalize([5, 5, 5, 5], window=2)


def test_percentile_median():
    assert percentile([1, 2, 3, 4, 5], 50) == pytest.approx(3.0)


def test_percentile_extremes():
    values = [10, 20, 30, 40]
    assert percentile(values, 0) == 10
    assert percentile(values, 100) == 40


def test_percentile_interpolation():
    # rank = 0.25 * 3 = 0.75 -> between index 0 (10) and 1 (20)
    assert percentile([10, 20, 30, 40], 25) == pytest.approx(17.5)


def test_percentile_rejects_out_of_range_q():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 150)


def test_winsorize_clips_tails():
    values = [1, 2, 3, 4, 100]
    result = winsorize(values, limits=(0.0, 0.2))
    assert result == [1, 2, 3, 4, 4]


def test_winsorize_no_op_with_zero_limits():
    values = [1, 5, 3, 100]
    assert winsorize(values, limits=(0.0, 0.0)) == values


def test_winsorize_rejects_invalid_limits():
    with pytest.raises(ValueError):
        winsorize([1, 2, 3], limits=(0.5, 0.0))


def test_relative_volume_known_value():
    assert relative_volume(150, average_volume=100) == pytest.approx(1.5)


def test_relative_volume_rejects_non_positive_average():
    with pytest.raises(ValueError):
        relative_volume(100, average_volume=0)
