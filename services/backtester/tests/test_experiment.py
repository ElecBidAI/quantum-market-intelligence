import pytest

from backtester.experiment import ExperimentRecord


def make_record(**overrides):
    defaults = dict(
        hypothesis="SMA crossover has positive edge on BTC-USDT 1h",
        dataset_version="binance-btcusdt-1h-2026-01-01_2026-06-01",
        transformations=["sma_20", "sma_50"],
        model_or_formula="sma_crossover_v1",
        parameters={"fast": 20, "slow": 50},
        cost_assumptions={"fee_bps": 10, "slippage_bps": 5, "spread_bps": 5},
        backtest_summary={"sharpe": 1.2, "max_drawdown": 0.15},
        walk_forward_summary=None,
        conclusion="Edge did not survive out-of-sample; rejected.",
        status="REJECTED",
    )
    return ExperimentRecord(**{**defaults, **overrides})


def test_valid_record_constructs():
    record = make_record()
    assert record.status == "REJECTED"
    assert record.tags == []


def test_rejects_empty_hypothesis():
    with pytest.raises(ValueError):
        make_record(hypothesis="   ")


def test_rejects_empty_dataset_version():
    with pytest.raises(ValueError):
        make_record(dataset_version="")


def test_rejects_empty_conclusion():
    with pytest.raises(ValueError):
        make_record(conclusion="")


def test_rejects_invalid_status():
    with pytest.raises(ValueError):
        make_record(status="MAYBE")


@pytest.mark.parametrize("status", ["REJECTED", "RESEARCH", "PAPER", "APPROVED"])
def test_accepts_every_valid_status(status):
    record = make_record(status=status)
    assert record.status == status


def test_optional_fields_default_to_none():
    record = make_record()
    assert record.monte_carlo_summary is None
    assert record.stress_test_summary is None
    assert record.risk_review is None
