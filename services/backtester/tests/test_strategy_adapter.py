import pytest
from regime_engine.classify import ALL_REGIME_LABELS

from backtester.strategy_adapter import strategy_to_position_fn


def make_bars(n: int) -> list[dict]:
    bars = []
    for i in range(n):
        close = 100.0 + i * 0.1
        bars.append(
            {
                "timestamp": f"t{i}",
                "open": close - 0.02,
                "high": close + 0.05,
                "low": close - 0.05,
                "close": close,
                "volume": 10.0,
            }
        )
    return bars


class _AlwaysAllowedStrategy:
    """Every regime is allowed — isolates tests from regime_engine's actual
    classification output, which isn't the thing under test here."""

    strategy_id = "fake_always_allowed_v1"
    allowed_regimes = frozenset(ALL_REGIME_LABELS)

    def __init__(self, candidate=None, raise_value_error=False):
        self._candidate = candidate
        self._raise = raise_value_error

    def generate(self, bars, regime, symbol, venue):
        if self._raise:
            raise ValueError("not enough bars for this strategy's own indicator window")
        return self._candidate


class _NeverAllowedStrategy:
    strategy_id = "fake_never_allowed_v1"
    allowed_regimes = frozenset()

    def generate(self, bars, regime, symbol, venue):
        raise AssertionError("must never be called when the regime isn't allowed")


def _candidate(direction: str, strength: float) -> dict:
    return {
        "strategyId": "fake",
        "symbol": "BTC-USDT",
        "venue": "binance",
        "direction": direction,
        "horizon": "1h",
        "signalStrength": strength,
        "entryLogic": {},
        "invalidationLogic": {},
        "stopLogic": {},
        "targetLogic": {},
        "expectedEdge": 0.01,
        "estimatedCosts": 0.002,
        "regime": "SIDEWAYS",
        "timestamp": "t59",
    }


def test_too_few_bars_returns_flat_without_calling_strategy():
    strategy = _NeverAllowedStrategy()  # would raise if ever called
    fn = strategy_to_position_fn(strategy, "BTC-USDT", "binance")
    assert fn(make_bars(10)) == 0.0  # below the default 50-bar classification floor


def test_regime_gate_blocks_a_strategy_with_no_allowed_regimes():
    strategy = _NeverAllowedStrategy()
    fn = strategy_to_position_fn(strategy, "BTC-USDT", "binance")
    assert fn(make_bars(60)) == 0.0


def test_value_error_from_generate_is_treated_as_no_signal():
    strategy = _AlwaysAllowedStrategy(raise_value_error=True)
    fn = strategy_to_position_fn(strategy, "BTC-USDT", "binance")
    assert fn(make_bars(60)) == 0.0


def test_none_candidate_is_flat():
    strategy = _AlwaysAllowedStrategy(candidate=None)
    fn = strategy_to_position_fn(strategy, "BTC-USDT", "binance")
    assert fn(make_bars(60)) == 0.0


@pytest.mark.parametrize(
    ("direction", "strength", "expected"),
    [("LONG", 0.7, 0.7), ("SHORT", 0.7, -0.7), ("NEUTRAL", 0.7, 0.0)],
)
def test_direction_sets_the_position_sign(direction, strength, expected):
    strategy = _AlwaysAllowedStrategy(candidate=_candidate(direction, strength))
    fn = strategy_to_position_fn(strategy, "BTC-USDT", "binance")
    assert fn(make_bars(60)) == pytest.approx(expected)
