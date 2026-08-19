from dataclasses import dataclass, field

from regime_engine.classify import RegimeResult

from strategy_engine.engine import run_strategies


@dataclass
class FakeStrategy:
    strategy_id: str
    allowed_regimes: frozenset[str]
    calls: list = field(default_factory=list)
    candidate_to_return: dict | None = None

    def generate(self, bars, regime, symbol, venue):
        self.calls.append((bars, regime, symbol, venue))
        return self.candidate_to_return


def make_regime(label: str) -> RegimeResult:
    return RegimeResult(label=label, confidence=0.8, metrics={})


def test_only_calls_strategies_whose_allowed_regimes_include_the_current_regime():
    allowed = FakeStrategy("allowed", frozenset({"BULLISH_TREND"}))
    disallowed = FakeStrategy("disallowed", frozenset({"SIDEWAYS"}))
    regime = make_regime("BULLISH_TREND")

    run_strategies(
        [allowed, disallowed], bars=[], regime=regime, symbol="BTC-USDT", venue="binance"
    )

    assert len(allowed.calls) == 1
    assert len(disallowed.calls) == 0


def test_disallowed_strategy_is_never_invoked_even_if_it_would_have_produced_a_candidate():
    disallowed = FakeStrategy(
        "disallowed", frozenset({"SIDEWAYS"}), candidate_to_return={"strategyId": "disallowed"}
    )
    regime = make_regime("BULLISH_TREND")

    result = run_strategies(
        [disallowed], bars=[], regime=regime, symbol="BTC-USDT", venue="binance"
    )

    assert result == []
    assert disallowed.calls == []


def test_collects_candidates_from_multiple_allowed_strategies():
    a = FakeStrategy("a", frozenset({"SIDEWAYS"}), candidate_to_return={"strategyId": "a"})
    b = FakeStrategy("b", frozenset({"SIDEWAYS"}), candidate_to_return={"strategyId": "b"})
    regime = make_regime("SIDEWAYS")

    result = run_strategies([a, b], bars=[], regime=regime, symbol="BTC-USDT", venue="binance")

    assert result == [{"strategyId": "a"}, {"strategyId": "b"}]


def test_skips_an_allowed_strategy_that_returns_none():
    silent = FakeStrategy("silent", frozenset({"SIDEWAYS"}), candidate_to_return=None)
    regime = make_regime("SIDEWAYS")

    result = run_strategies([silent], bars=[], regime=regime, symbol="BTC-USDT", venue="binance")

    assert result == []


def test_no_strategies_no_candidates():
    regime = make_regime("SIDEWAYS")
    assert run_strategies([], bars=[], regime=regime, symbol="BTC-USDT", venue="binance") == []
