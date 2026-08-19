import pytest

from quant_core.stats import (
    autocorrelation,
    confidence_interval_mean,
    covariance,
    iqr,
    kendall_tau,
    kurtosis,
    mad,
    mean,
    median,
    pearson_correlation,
    rolling_correlation,
    skewness,
    spearman_correlation,
    std_dev,
    variance,
)


def test_mean_median():
    assert mean([1, 2, 3, 4, 5]) == pytest.approx(3.0)
    assert median([1, 2, 3, 4, 5]) == 3
    assert median([1, 2, 3, 4]) == pytest.approx(2.5)


def test_variance_and_std_dev_sample():
    # classic textbook example: sample variance = 4.571428..., std = 2.13809...
    values = [2, 4, 4, 4, 5, 5, 7, 9]
    assert variance(values) == pytest.approx(4.571428571428571)
    assert std_dev(values) == pytest.approx(2.1380899352993947)


def test_variance_rejects_single_value():
    with pytest.raises(ValueError):
        variance([1])


def test_mad_known_value():
    assert mad([1, 2, 3, 4, 5]) == pytest.approx(1.2)


def test_iqr_known_value():
    assert iqr([1, 2, 3, 4, 5, 6, 7, 8]) == pytest.approx(3.5)


def test_skewness_known_value():
    # right-skewed set; reference value computed independently (see commit context)
    assert skewness([1, 2, 3, 4, 10]) == pytest.approx(1.2143146215046576)


def test_skewness_symmetric_data_is_near_zero():
    assert skewness([1, 2, 3, 4, 5]) == pytest.approx(0.0, abs=1e-9)


def test_kurtosis_known_value():
    assert kurtosis([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(-0.42827148437500084)


def test_covariance_and_pearson_perfect_linear_relationship():
    x = [1, 2, 3]
    y = [2, 4, 6]
    assert covariance(x, y) == pytest.approx(2.0)
    assert pearson_correlation(x, y) == pytest.approx(1.0)


def test_pearson_perfect_negative_relationship():
    x = [1, 2, 3]
    y = [6, 4, 2]
    assert pearson_correlation(x, y) == pytest.approx(-1.0)


def test_pearson_rejects_zero_variance_series():
    with pytest.raises(ValueError):
        pearson_correlation([1, 1, 1], [1, 2, 3])


def test_spearman_known_value():
    x = [1, 2, 3, 4, 5]
    y = [2, 1, 4, 3, 5]
    assert spearman_correlation(x, y) == pytest.approx(0.7999999999999998)


def test_kendall_tau_known_value():
    x = [1, 2, 3, 4, 5]
    y = [2, 1, 4, 3, 5]
    assert kendall_tau(x, y) == pytest.approx(0.6)


def test_kendall_tau_perfect_agreement():
    assert kendall_tau([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


def test_rolling_correlation_perfect_relationship_throughout():
    x = [1, 2, 3, 4, 5]
    y = [2, 4, 6, 8, 10]
    result = rolling_correlation(x, y, window=3)
    assert len(result) == 3
    for value in result:
        assert value == pytest.approx(1.0)


def test_autocorrelation_lag_one_perfect_trend():
    values = [1, 2, 3, 4, 5, 6]
    assert autocorrelation(values, lag=1) == pytest.approx(1.0)


def test_autocorrelation_rejects_lag_too_large():
    with pytest.raises(ValueError):
        autocorrelation([1, 2, 3], lag=3)


def test_confidence_interval_mean_known_value():
    values = list(range(1, 31))
    lower, upper = confidence_interval_mean(values, confidence=0.95)
    assert lower == pytest.approx(12.349798638161921)
    assert upper == pytest.approx(18.65020136183808)


def test_confidence_interval_mean_rejects_invalid_confidence():
    with pytest.raises(ValueError):
        confidence_interval_mean([1, 2, 3], confidence=1.5)
