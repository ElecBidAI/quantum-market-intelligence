import pytest

from strategy_engine.scoring import (
    confidence_score,
    net_edge_score,
    opportunity_score,
    risk_score,
    weighted_score,
)


def test_weighted_score_known_value():
    result = weighted_score({"trend": 80, "momentum": 60}, {"trend": 2, "momentum": 1})
    assert result == pytest.approx(220 / 3)


def test_weighted_score_equal_weights_is_a_plain_average():
    result = weighted_score({"a": 10, "b": 20, "c": 30}, {"a": 1, "b": 1, "c": 1})
    assert result == pytest.approx(20.0)


def test_weighted_score_rejects_out_of_range_component():
    with pytest.raises(ValueError):
        weighted_score({"trend": 150}, {"trend": 1})


def test_weighted_score_rejects_missing_weight():
    with pytest.raises(ValueError):
        weighted_score({"trend": 50, "momentum": 50}, {"trend": 1})


def test_weighted_score_rejects_empty_components():
    with pytest.raises(ValueError):
        weighted_score({}, {"trend": 1})


def test_opportunity_score_uses_default_weights_when_none_supplied():
    result = opportunity_score({"trend": 100, "momentum": 100})
    assert result == pytest.approx(100.0)


def test_opportunity_score_accepts_custom_weights():
    result = opportunity_score({"trend": 80}, weights={"trend": 3})
    assert result == pytest.approx(80.0)


def test_risk_score_known_value():
    weights = {"volatility": 1, "drawdown": 1}
    result = risk_score({"volatility": 40, "drawdown": 20}, weights=weights)
    assert result == pytest.approx(30.0)


def test_confidence_score_known_value():
    result = confidence_score({"data_quality": 90}, weights={"data_quality": 1})
    assert result == pytest.approx(90.0)


def test_net_edge_score_known_value():
    # NetEdge = 80 * (1 - 30/100) * (70/100) = 80 * 0.7 * 0.7 = 39.2
    assert net_edge_score(opportunity=80, risk=30, confidence=70) == pytest.approx(39.2)


def test_net_edge_score_zero_confidence_is_zero_regardless_of_opportunity():
    assert net_edge_score(opportunity=100, risk=0, confidence=0) == pytest.approx(0.0)


def test_net_edge_score_max_risk_is_zero_regardless_of_opportunity():
    assert net_edge_score(opportunity=100, risk=100, confidence=100) == pytest.approx(0.0)


def test_net_edge_score_rejects_out_of_range_inputs():
    with pytest.raises(ValueError):
        net_edge_score(opportunity=150, risk=0, confidence=100)
    with pytest.raises(ValueError):
        net_edge_score(opportunity=50, risk=-10, confidence=100)
