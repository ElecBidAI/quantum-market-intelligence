import pytest

from ai_council.agents.devils_advocate import DevilsAdvocate


def test_a_clean_candidate_is_neutral_never_support(make_candidate, make_context, make_regime):
    context = make_context(
        candidate=make_candidate(signalStrength=0.8, expectedEdge=0.05, estimatedCosts=0.002),
        regime=make_regime(confidence=0.9),
    )
    opinion = DevilsAdvocate().analyze(context)
    assert opinion.stance == "NEUTRAL"
    assert opinion.confidence == pytest.approx(0.0)
    assert opinion.findings == []


def test_low_regime_confidence_is_flagged(make_context, make_regime):
    context = make_context(regime=make_regime(confidence=0.3))
    opinion = DevilsAdvocate().analyze(context)
    assert opinion.stance == "OPPOSE"
    assert any(f.code == "LOW_REGIME_CONFIDENCE" for f in opinion.findings)


def test_weak_signal_strength_is_flagged(make_candidate, make_context):
    context = make_context(candidate=make_candidate(signalStrength=0.1))
    opinion = DevilsAdvocate().analyze(context)
    assert any(f.code == "WEAK_SIGNAL_STRENGTH" for f in opinion.findings)


def test_thin_edge_margin_is_flagged(make_candidate, make_context):
    context = make_context(candidate=make_candidate(expectedEdge=0.001, estimatedCosts=0.01))
    opinion = DevilsAdvocate().analyze(context)
    assert any(f.code == "THIN_EDGE_MARGIN" for f in opinion.findings)


def test_everything_wrong_gives_full_confidence_opposition(
    make_candidate, make_context, make_regime
):
    context = make_context(
        candidate=make_candidate(signalStrength=0.1, expectedEdge=0.001, estimatedCosts=0.01),
        regime=make_regime(confidence=0.2),
    )
    opinion = DevilsAdvocate().analyze(context)
    assert opinion.stance == "OPPOSE"
    assert opinion.confidence == pytest.approx(1.0)
    assert len(opinion.findings) == 3


def test_low_backtest_win_rate_adds_a_fourth_check(make_context):
    context = make_context(backtest_summary={"win_rate": 0.2})
    opinion = DevilsAdvocate().analyze(context)
    assert any(f.code == "LOW_HISTORICAL_WIN_RATE" for f in opinion.findings)
    assert opinion.confidence == pytest.approx(0.25)  # 1 finding out of 4 checks


def test_missing_win_rate_in_backtest_summary_does_not_count_as_a_check(make_context):
    context = make_context(backtest_summary={"trade_count": 0, "win_rate": None})
    opinion = DevilsAdvocate().analyze(context)
    assert opinion.confidence == pytest.approx(0.0)
