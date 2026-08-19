import pytest

from risk_engine.limits import RiskLimits
from risk_engine.state import CandidateRequest, MarketContext, PortfolioState


def test_risk_limits_defaults_are_valid():
    RiskLimits()  # must not raise


def test_risk_limits_rejects_non_positive_field():
    with pytest.raises(ValueError):
        RiskLimits(max_position_pct=0)


def test_risk_limits_allows_none_var_limit():
    RiskLimits(max_portfolio_var_pct=None)  # must not raise


def test_risk_limits_rejects_non_positive_var_limit_when_set():
    with pytest.raises(ValueError):
        RiskLimits(max_portfolio_var_pct=0)


def test_candidate_request_rejects_invalid_direction():
    with pytest.raises(ValueError):
        CandidateRequest(
            strategy_id="s", symbol="BTC-USDT", direction="SIDEWAYS", requested_size_pct=0.05
        )


def test_candidate_request_rejects_non_positive_size():
    with pytest.raises(ValueError):
        CandidateRequest(strategy_id="s", symbol="BTC-USDT", direction="LONG", requested_size_pct=0)


def test_portfolio_state_gross_and_net_exposure():
    state = PortfolioState(equity=1000, position_pct_by_symbol={"BTC-USDT": 0.1, "ETH-USDT": -0.05})
    assert state.gross_exposure_pct == pytest.approx(0.15)
    assert state.net_exposure_pct == pytest.approx(0.05)


def test_portfolio_state_position_pct_defaults_to_zero():
    state = PortfolioState(equity=1000)
    assert state.position_pct("BTC-USDT") == 0.0


def test_portfolio_state_rejects_non_positive_equity():
    with pytest.raises(ValueError):
        PortfolioState(equity=0)


def test_market_context_rejects_negative_spread():
    with pytest.raises(ValueError):
        MarketContext(spread_bps=-1, data_age_seconds=1)
