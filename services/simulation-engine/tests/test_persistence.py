from simulation_engine.monte_carlo import run_trade_sequence_monte_carlo
from simulation_engine.persistence import insert_simulation_run, monte_carlo_result_to_json


class FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))


def test_insert_simulation_run_issues_expected_sql_and_params():
    cursor = FakeCursor()
    insert_simulation_run(
        cursor,
        run_type="monte_carlo_trade_sequence",
        strategy_id="sma_crossover_v1",
        dataset_version="binance-btcusdt-1h-v1",
        parameters={"n_simulations": 1000},
        results={"probability_of_ruin": 0.02},
        created_at="2026-08-19T00:00:00Z",
    )

    query, params = cursor.executed[0]
    assert "INSERT INTO simulation_runs" in query
    assert params[0] == "monte_carlo_trade_sequence"
    assert params[1] == "sma_crossover_v1"
    assert '"n_simulations": 1000' in params[3]
    assert '"probability_of_ruin": 0.02' in params[4]


def test_insert_simulation_run_allows_null_strategy_id():
    cursor = FakeCursor()
    insert_simulation_run(
        cursor,
        run_type="stress_test",
        strategy_id=None,
        dataset_version="binance-btcusdt-1h-v1",
        parameters={},
        results={},
        created_at="2026-08-19T00:00:00Z",
    )
    _, params = cursor.executed[0]
    assert params[1] is None


def test_monte_carlo_result_to_json_is_json_serializable():
    import json

    result = run_trade_sequence_monte_carlo(
        [0.01, -0.02, 0.03], path_length=10, n_simulations=50, seed=1
    )
    payload = monte_carlo_result_to_json(result)
    serialized = json.dumps(payload)  # must not raise
    assert json.loads(serialized)["n_simulations"] == 50
