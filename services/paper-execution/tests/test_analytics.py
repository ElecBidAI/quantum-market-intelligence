import pytest

from paper_execution.analytics import summarize_trades


def test_summarize_trades_known_values():
    # 3 wins, 2 losses — same shape of data used in backtester's own metrics tests
    trades = [0.05, -0.02, 0.03, -0.01, -0.04]
    summary = summarize_trades(trades)

    assert summary["trade_count"] == 5
    assert summary["win_rate"] == pytest.approx(0.4)
    assert summary["expectancy"] == pytest.approx(0.002)
    assert summary["payoff_ratio"] == pytest.approx(1.7142857142857142)
    assert summary["profit_factor"] == pytest.approx(1.1428571428571428)


def test_summarize_trades_empty_returns_all_none():
    summary = summarize_trades([])
    assert summary["trade_count"] == 0
    assert summary["win_rate"] is None
    assert summary["expectancy"] is None
    assert summary["payoff_ratio"] is None
    assert summary["profit_factor"] is None


def test_summarize_trades_all_wins_leaves_payoff_ratio_undefined_not_zero():
    summary = summarize_trades([0.01, 0.02, 0.03])
    assert summary["trade_count"] == 3
    assert summary["win_rate"] == pytest.approx(1.0)
    assert summary["payoff_ratio"] is None  # no losses to compare against
    assert summary["profit_factor"] is None  # no losses; ratio undefined (would be infinite)


def test_summarize_trades_all_losses():
    summary = summarize_trades([-0.01, -0.02])
    assert summary["win_rate"] == pytest.approx(0.0)
    assert summary["payoff_ratio"] is None  # no wins to compare against
