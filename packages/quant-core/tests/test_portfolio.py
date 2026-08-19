import pytest

from quant_core.portfolio import (
    component_risk_contribution,
    diversification_ratio,
    expected_return,
    marginal_risk_contribution,
    max_sharpe_weights,
    min_variance_weights,
    risk_parity_weights,
    variance,
    volatility,
)

MU = [0.08, 0.12, 0.10]
COV = [
    [0.04, 0.01, 0.015],
    [0.01, 0.09, 0.02],
    [0.015, 0.02, 0.0625],
]
WEIGHTS = [0.4, 0.35, 0.25]


def test_expected_return_known_value():
    assert expected_return(WEIGHTS, MU) == pytest.approx(0.099)


def test_expected_return_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        expected_return([0.5, 0.5], MU)


def test_variance_and_volatility_known_values():
    assert variance(WEIGHTS, COV) == pytest.approx(0.03063125)
    assert volatility(WEIGHTS, COV) == pytest.approx(0.17501785623187138)


def test_variance_rejects_non_square_covariance():
    with pytest.raises(ValueError):
        variance(WEIGHTS, [[0.04, 0.01], [0.01, 0.09]])


def test_min_variance_weights_known_value():
    weights = min_variance_weights(COV)
    assert weights == pytest.approx([0.5555555555555555, 0.19259259259259262, 0.2518518518518519])
    # the minimum-variance portfolio must indeed have lower variance than an arbitrary one
    assert variance(weights, COV) < variance(WEIGHTS, COV)


def test_min_variance_weights_sum_to_one():
    weights = min_variance_weights(COV)
    assert sum(weights) == pytest.approx(1.0)


def test_max_sharpe_weights_known_value():
    weights = max_sharpe_weights(MU, COV, risk_free_rate=0.0)
    assert weights == pytest.approx([0.4217252396166134, 0.2907348242811502, 0.2875399361022365])
    assert sum(weights) == pytest.approx(1.0)


def test_diversification_ratio_known_value():
    assert diversification_ratio(WEIGHTS, COV) == pytest.approx(1.4141414215021642)


def test_diversification_ratio_is_one_for_a_single_asset():
    assert diversification_ratio([1.0], [[0.04]]) == pytest.approx(1.0)


def test_marginal_and_component_risk_contribution_known_values():
    mrc = marginal_risk_contribution(WEIGHTS, COV)
    assert mrc == pytest.approx([0.13284358808050634, 0.23140495988217233, 0.16355474016363414])

    crc = component_risk_contribution(WEIGHTS, COV)
    assert crc == pytest.approx([0.05313743523220254, 0.08099173595876032, 0.040888685040908535])
    # component contributions must sum to total portfolio volatility
    assert sum(crc) == pytest.approx(volatility(WEIGHTS, COV))


def test_risk_parity_weights_known_value_and_equal_contributions():
    weights = risk_parity_weights(COV)
    assert weights == pytest.approx(
        [0.4099110023396897, 0.27710641070572617, 0.3129825869545842], abs=1e-6
    )
    # the defining property: every asset contributes equal risk
    crc = component_risk_contribution(weights, COV)
    assert crc[0] == pytest.approx(crc[1], abs=1e-6)
    assert crc[1] == pytest.approx(crc[2], abs=1e-6)


def test_risk_parity_weights_sum_to_one():
    weights = risk_parity_weights(COV)
    assert sum(weights) == pytest.approx(1.0)


def test_risk_parity_weights_reduce_to_equal_weights_for_identical_assets():
    identical_cov = [[0.04, 0.02, 0.02], [0.02, 0.04, 0.02], [0.02, 0.02, 0.04]]
    weights = risk_parity_weights(identical_cov)
    assert weights == pytest.approx([1 / 3, 1 / 3, 1 / 3], abs=1e-6)
