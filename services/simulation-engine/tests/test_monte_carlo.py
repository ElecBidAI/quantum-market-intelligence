import numpy as np
import pytest

from simulation_engine.monte_carlo import (
    bootstrap_trade_sequences,
    equity_curves,
    expected_shortfall,
    longest_loss_streak_distribution,
    percentiles,
    probability_of_drawdown_exceeding,
    probability_of_loss,
    probability_of_ruin,
    recovery_time_distribution,
    run_trade_sequence_monte_carlo,
    terminal_multipliers,
)

# Hand-traced fixture (see commit context for the full trace):
#   path0: [0.1, -0.05, 0.2, -0.1]   -> terminal multiplier 1.1286
#   path1: [-0.05, -0.05, -0.05, 0.3] -> terminal multiplier 1.1145875
TRADE_SEQUENCES = np.array([[0.1, -0.05, 0.2, -0.1], [-0.05, -0.05, -0.05, 0.3]])


def test_bootstrap_trade_sequences_deterministic_and_shaped():
    a = bootstrap_trade_sequences([0.01, -0.02, 0.03], path_length=5, n_simulations=4, seed=1)
    b = bootstrap_trade_sequences([0.01, -0.02, 0.03], path_length=5, n_simulations=4, seed=1)
    assert a.shape == (4, 5)
    assert np.array_equal(a, b)
    assert np.all(np.isin(a, [0.01, -0.02, 0.03]))


def test_terminal_multipliers_known_value():
    result = terminal_multipliers(TRADE_SEQUENCES)
    assert result == pytest.approx([1.1286, 1.1145875])


def test_equity_curves_known_value():
    curves = equity_curves(TRADE_SEQUENCES, initial_equity=1.0)
    assert curves[0].tolist() == pytest.approx([1.0, 1.1, 1.045, 1.254, 1.1286])
    assert curves[1].tolist() == pytest.approx([1.0, 0.95, 0.9025, 0.857375, 1.1145875])


def test_percentiles_structural():
    result = percentiles(np.array([1.0, 2.0, 3.0, 4.0, 5.0]), ps=(0, 50, 100))
    assert result == {0: 1.0, 50: 3.0, 100: 5.0}


def test_probability_of_loss_known_value():
    multipliers = terminal_multipliers(TRADE_SEQUENCES)
    # both paths end above their starting equity
    assert probability_of_loss(multipliers) == pytest.approx(0.0)


def test_probability_of_loss_with_a_losing_path():
    multipliers = np.array([1.2, 0.9, 1.1, 0.8])
    assert probability_of_loss(multipliers) == pytest.approx(0.5)


def test_probability_of_drawdown_exceeding_known_value():
    curves = equity_curves(TRADE_SEQUENCES)
    # path0 max_dd = 0.1, path1 max_dd = 0.142625
    assert probability_of_drawdown_exceeding(curves, threshold=0.11) == pytest.approx(0.5)
    assert probability_of_drawdown_exceeding(curves, threshold=0.2) == pytest.approx(0.0)


def test_probability_of_ruin_known_value():
    curves = equity_curves(TRADE_SEQUENCES)
    # path0 never drops below 0.9 * 1.0; path1 drops to 0.857375
    assert probability_of_ruin(curves, ruin_threshold=0.9) == pytest.approx(0.5)


def test_probability_of_ruin_rejects_invalid_threshold():
    curves = equity_curves(TRADE_SEQUENCES)
    with pytest.raises(ValueError):
        probability_of_ruin(curves, ruin_threshold=1.5)


def test_recovery_time_distribution_known_value():
    curves = equity_curves(TRADE_SEQUENCES)
    assert recovery_time_distribution(curves) == [None, 1]


def test_recovery_time_distribution_zero_for_monotonic_growth():
    curves = np.array([[1.0, 1.1, 1.2, 1.3]])
    assert recovery_time_distribution(curves) == [0]


def test_longest_loss_streak_distribution_known_value():
    assert longest_loss_streak_distribution(TRADE_SEQUENCES) == [1, 3]


def test_expected_shortfall_delegates_to_quant_core_cvar():
    from quant_core.risk import cvar

    returns = [-0.05, -0.03, 0.01, 0.02, -0.01]
    expected = cvar(returns, confidence=0.8)
    assert expected_shortfall(returns, confidence=0.8) == pytest.approx(expected)


class TestRunTradeSequenceMonteCarlo:
    def test_reproducible_end_to_end(self):
        trade_returns = [0.02, -0.01, 0.03, -0.02, 0.01, -0.015]
        a = run_trade_sequence_monte_carlo(trade_returns, path_length=20, n_simulations=500, seed=7)
        b = run_trade_sequence_monte_carlo(trade_returns, path_length=20, n_simulations=500, seed=7)
        assert a == b

    def test_output_shape_and_bounds(self):
        trade_returns = [0.02, -0.01, 0.03, -0.02, 0.01, -0.015]
        result = run_trade_sequence_monte_carlo(
            trade_returns, path_length=20, n_simulations=500, seed=7
        )
        assert result.n_simulations == 500
        assert result.path_length == 20
        assert 0.0 <= result.probability_of_loss <= 1.0
        assert 0.0 <= result.probability_of_ruin <= 1.0
        assert 0.0 <= result.probability_of_drawdown_exceeding_threshold <= 1.0
        assert len(result.recovery_times) == 500
        assert len(result.longest_loss_streaks) == 500
        assert set(result.terminal_multiplier_percentiles.keys()) == {1, 5, 25, 50, 75, 95, 99}

    def test_all_positive_trades_never_lose_or_ruin(self):
        result = run_trade_sequence_monte_carlo(
            [0.01, 0.02, 0.03], path_length=10, n_simulations=100, seed=1
        )
        assert result.probability_of_loss == pytest.approx(0.0)
        assert result.probability_of_ruin == pytest.approx(0.0)
        assert all(streak == 0 for streak in result.longest_loss_streaks)
