import pytest

from quant_core.derivatives import (
    annualized_basis,
    annualized_funding_rate,
    basis,
    basis_pct,
    funding_pnl,
    leverage,
    liquidation_buffer_pct,
    liquidation_price,
    open_interest_change,
    open_interest_change_pct,
)


def test_basis_known_value():
    assert basis(65000, 65200) == pytest.approx(200)


def test_basis_rejects_non_positive_prices():
    with pytest.raises(ValueError):
        basis(0, 65200)


def test_basis_pct_known_value():
    assert basis_pct(65000, 65200) == pytest.approx(0.003076923076923077)


def test_annualized_basis_known_value():
    assert annualized_basis(65000, 65650, 30) == pytest.approx(0.12166666666666666)


def test_annualized_basis_rejects_non_positive_days():
    with pytest.raises(ValueError):
        annualized_basis(65000, 65650, 0)


def test_annualized_funding_rate_known_value():
    assert annualized_funding_rate(0.0001, fundings_per_day=3) == pytest.approx(0.1095)


def test_annualized_funding_rate_rejects_non_positive_frequency():
    with pytest.raises(ValueError):
        annualized_funding_rate(0.0001, fundings_per_day=0)


def test_funding_pnl_long_pays_when_rate_is_positive():
    assert funding_pnl(100_000, 0.0001, direction=1) == pytest.approx(-10.0)


def test_funding_pnl_short_receives_when_rate_is_positive():
    assert funding_pnl(100_000, 0.0001, direction=-1) == pytest.approx(10.0)


def test_funding_pnl_rejects_invalid_direction():
    with pytest.raises(ValueError):
        funding_pnl(100_000, 0.0001, direction=0)


def test_leverage_known_value():
    assert leverage(50_000, 10_000) == pytest.approx(5.0)


def test_leverage_rejects_non_positive_equity():
    with pytest.raises(ValueError):
        leverage(50_000, 0)


def test_liquidation_price_long_known_value():
    result = liquidation_price(65000, leverage_=10, direction=1, maintenance_margin_rate=0.005)
    assert result == pytest.approx(58825.0)


def test_liquidation_price_short_known_value():
    result = liquidation_price(65000, leverage_=10, direction=-1, maintenance_margin_rate=0.005)
    assert result == pytest.approx(71175.00000000001)


def test_liquidation_price_rejects_invalid_maintenance_margin():
    with pytest.raises(ValueError):
        liquidation_price(65000, leverage_=10, direction=1, maintenance_margin_rate=1.0)


def test_liquidation_buffer_pct_known_value():
    liq_long = liquidation_price(65000, leverage_=10, direction=1, maintenance_margin_rate=0.005)
    result = liquidation_buffer_pct(65000, liq_long, direction=1)
    assert result == pytest.approx(0.095)


def test_liquidation_buffer_pct_zero_at_the_liquidation_price():
    liq_long = liquidation_price(65000, leverage_=10, direction=1, maintenance_margin_rate=0.005)
    assert liquidation_buffer_pct(liq_long, liq_long, direction=1) == pytest.approx(0.0)


def test_open_interest_change_known_value():
    assert open_interest_change(1000, 1250) == pytest.approx(250)


def test_open_interest_change_pct_known_value():
    assert open_interest_change_pct(1000, 1250) == pytest.approx(0.25)


def test_open_interest_change_rejects_negative_values():
    with pytest.raises(ValueError):
        open_interest_change(-1, 100)
