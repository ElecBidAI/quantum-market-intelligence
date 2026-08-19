import pytest

from ai_council.agents.auditor import Auditor


def test_consistent_candidate_is_supported_with_full_confidence(make_context):
    opinion = Auditor().analyze(make_context())
    assert opinion.stance == "SUPPORT"
    assert opinion.confidence == pytest.approx(1.0)
    assert opinion.findings == []


def test_regime_mismatch_is_caught(make_candidate, make_context, make_regime):
    context = make_context(
        candidate=make_candidate(regime="BULLISH_TREND"),
        regime=make_regime(label="SIDEWAYS"),
    )
    opinion = Auditor().analyze(context)
    assert opinion.stance == "OPPOSE"
    assert any(f.code == "REGIME_MISMATCH" for f in opinion.findings)


def test_missing_strategy_id_is_caught(make_candidate, make_context):
    context = make_context(candidate=make_candidate(strategyId=""))
    opinion = Auditor().analyze(context)
    assert any(f.code == "MISSING_STRATEGY_ID" for f in opinion.findings)


def test_long_with_stop_above_entry_is_inconsistent(make_candidate, make_context):
    candidate = make_candidate(
        direction="LONG",
        entryLogic={"entryPrice": 100.0},
        stopLogic={"stopPrice": 105.0},  # wrong side for a LONG stop
        targetLogic={"targetPrice": 110.0},
    )
    opinion = Auditor().analyze(make_context(candidate=candidate))
    assert opinion.stance == "OPPOSE"
    assert any(f.code == "INCONSISTENT_STOP_TARGET_ORDERING" for f in opinion.findings)


def test_short_with_correct_ordering_is_consistent(make_candidate, make_context):
    candidate = make_candidate(
        direction="SHORT",
        entryLogic={"entryPrice": 100.0},
        stopLogic={"stopPrice": 105.0},
        targetLogic={"targetPrice": 90.0},
    )
    opinion = Auditor().analyze(make_context(candidate=candidate))
    assert opinion.stance == "SUPPORT"


def test_missing_price_fields_skips_ordering_check_without_crashing(make_candidate, make_context):
    candidate = make_candidate(entryLogic={}, stopLogic={}, targetLogic={})
    opinion = Auditor().analyze(make_context(candidate=candidate))
    assert opinion.stance == "SUPPORT"  # nothing else wrong, ordering check just skipped


def test_multiple_findings_reduce_confidence(make_candidate, make_context, make_regime):
    candidate = make_candidate(
        strategyId="", regime="SIDEWAYS", entryLogic={}, stopLogic={}, targetLogic={}
    )
    context = make_context(candidate=candidate, regime=make_regime(label="BULLISH_TREND"))
    opinion = Auditor().analyze(context)
    # 2 findings (regime mismatch, missing id) out of 2 base checks (no price fields -> the
    # ordering check is skipped and doesn't add a third) -> full-strength opposition
    assert len(opinion.findings) == 2
    assert opinion.confidence == pytest.approx(1.0)
