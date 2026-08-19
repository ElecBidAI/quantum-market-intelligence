from backtester.experiment import ExperimentRecord
from backtester.persistence import insert_backtest, insert_research_run


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))


def test_insert_backtest_issues_expected_sql_and_params():
    cursor = FakeCursor()
    insert_backtest(
        cursor,
        strategy_id="sma_crossover_v1",
        symbol="BTC-USDT",
        interval="1h",
        dataset_version="binance-btcusdt-1h-v1",
        parameters={"fast": 20, "slow": 50},
        cost_assumptions={"fee_bps": 10},
        metrics={"sharpe": 1.2},
        created_at="2026-08-19T00:00:00Z",
    )

    query, params = cursor.executed[0]
    assert "INSERT INTO backtests" in query
    assert params[0] == "sma_crossover_v1"
    assert params[1] == "BTC-USDT"
    assert params[2] == "1h"
    assert '"fast": 20' in params[4]
    assert '"sharpe": 1.2' in params[6]


def test_insert_research_run_issues_expected_sql_and_params():
    cursor = FakeCursor()
    record = ExperimentRecord(
        hypothesis="SMA crossover has positive edge",
        dataset_version="binance-btcusdt-1h-v1",
        transformations=["sma_20"],
        model_or_formula="sma_crossover_v1",
        parameters={"fast": 20},
        cost_assumptions={"fee_bps": 10},
        backtest_summary={"sharpe": 1.2},
        walk_forward_summary=None,
        conclusion="Rejected out of sample.",
        status="REJECTED",
    )

    insert_research_run(cursor, record, created_at="2026-08-19T00:00:00Z")

    query, params = cursor.executed[0]
    assert "INSERT INTO research_runs" in query
    assert params[0] == "SMA crossover has positive edge"
    assert params[1] == "binance-btcusdt-1h-v1"
    assert params[12] == "REJECTED"
