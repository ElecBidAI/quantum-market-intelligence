from ai_council.narrator import DISCLAIMER, generate_narrative
from ai_council.opinion import AgentOpinion, Finding

DENYLIST = ["guaranteed", "will profit", "buy now", "can't lose", "sure thing", "moon"]


def test_no_candidate_branch(make_regime):
    regime = make_regime(label="SIDEWAYS", confidence=0.6)
    narrative = generate_narrative("BTC-USDT", regime, None, None, [], None)

    assert "None of the three strategies" in narrative
    assert "SIDEWAYS" in narrative
    assert DISCLAIMER in narrative


def test_multi_candidate_disclosure(make_candidate, make_regime, approve_decision, make_thesis):
    candidate = make_candidate(expectedEdge=0.08)
    thesis = make_thesis()
    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        candidate,
        approve_decision(),
        thesis.opinions,
        thesis,
        candidate_pool_size=3,
    )
    assert "3 strategies generated candidates" in narrative
    assert "selected because it had the highest expected edge (0.0800)" in narrative


def test_reject_branch(make_candidate, make_regime, reject_decision, make_thesis):
    decision = reject_decision()
    reason = decision["reasons"][0]
    veto_officer = AgentOpinion(
        "risk_officer", "VETO", 1.0, [Finding(reason["code"], reason["detail"])]
    )
    thesis = make_thesis(opinions=[veto_officer], final_stance="VETO", weighted_score=-1.0)

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), make_candidate(), decision, thesis.opinions, thesis
    )

    assert "I'd pass on this one" in narrative
    assert "breached" in narrative
    assert "the day's loss limit is already breached" in narrative
    assert "the analytical agents don't get a separate say here" in narrative
    assert DISCLAIMER in narrative


def test_reduce_branch(make_candidate, make_regime, reduce_decision, make_thesis):
    decision = reduce_decision(adjustment=0.5)
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), make_candidate(), decision, thesis.opinions, thesis
    )

    assert "cut to 50%" in narrative
    assert "the position size limit for this asset (capped)" in narrative
    assert "came back" in narrative  # council summary sentence
    assert DISCLAIMER in narrative


def test_approve_support_branch(make_candidate, make_regime, approve_decision, make_thesis):
    thesis = make_thesis(final_stance="SUPPORT", weighted_score=1.0)

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), make_candidate(), approve_decision(), thesis.opinions, thesis
    )

    assert "Risk management cleared this at full requested size" in narrative
    assert "No limits were binding" in narrative
    assert "isn't a clean read internally" not in narrative
    assert DISCLAIMER in narrative


def test_approve_disagreement_branch(make_candidate, make_regime, approve_decision, make_thesis):
    dissenter = AgentOpinion(
        "devils_advocate",
        "OPPOSE",
        0.5,
        [Finding("THIN_EDGE_MARGIN", "ratio 1.20 < 1.5")],
    )
    opinions = [
        AgentOpinion("quant_agent", "SUPPORT", 0.9, []),
        AgentOpinion("risk_officer", "SUPPORT", 1.0, []),
        dissenter,
        AgentOpinion("auditor_agent", "SUPPORT", 1.0, []),
    ]
    thesis = make_thesis(opinions=opinions, final_stance="NEUTRAL", weighted_score=0.1)

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), make_candidate(), approve_decision(), opinions, thesis
    )

    assert "Risk management cleared this at full requested size" in narrative
    assert "isn't a clean read internally" in narrative
    assert "the edge over costs looks thin" in narrative
    assert "ratio 1.20 < 1.5" in narrative
    assert "not a reason to override risk's decision" in narrative
    assert DISCLAIMER in narrative


def test_missing_entry_stop_target_prices(
    make_candidate, make_regime, approve_decision, make_thesis
):
    candidate = make_candidate(entryLogic={}, stopLogic={}, targetLogic={})
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), candidate, approve_decision(), thesis.opinions, thesis
    )

    assert "didn't populate explicit entry/stop/target prices" in narrative


def test_present_entry_stop_target_prices_are_not_invented(
    make_candidate, make_regime, approve_decision, make_thesis
):
    candidate = make_candidate(
        entryLogic={"entryPrice": 100.0},
        stopLogic={"stopPrice": 95.0},
        targetLogic={"targetPrice": 110.0},
    )
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), candidate, approve_decision(), thesis.opinions, thesis
    )

    assert "entry around 100.0" in narrative
    assert "a stop at 95.0" in narrative
    assert "a target at 110.0" in narrative


def test_expected_edge_and_costs_are_not_invented(
    make_candidate, make_regime, approve_decision, make_thesis
):
    candidate = make_candidate(expectedEdge=0.0512, estimatedCosts=0.0099)
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT", make_regime(), candidate, approve_decision(), thesis.opinions, thesis
    )

    assert "0.0512" in narrative
    assert "0.0099" in narrative
    assert "not a validated profit forecast" in narrative


def test_requires_risk_decision_and_thesis_when_candidate_given(make_candidate, make_regime):
    try:
        generate_narrative("BTC-USDT", make_regime(), make_candidate(), None, [], None)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_unrecognized_decision_raises(make_candidate, make_regime, make_thesis):
    bad_decision = {"decision": "MAYBE", "reasons": [], "sizingAdjustment": None}
    thesis = make_thesis()
    try:
        generate_narrative(
            "BTC-USDT", make_regime(), make_candidate(), bad_decision, thesis.opinions, thesis
        )
        raised = False
    except ValueError:
        raised = True
    assert raised


def _all_branch_narratives(
    make_candidate, make_regime, approve_decision, reduce_decision, reject_decision, make_thesis
):
    approve_thesis = make_thesis()
    reduce_thesis = make_thesis()
    reject_finding = [Finding("MAX_DAILY_LOSS", "breached")]
    reject_thesis = make_thesis(
        opinions=[AgentOpinion("risk_officer", "VETO", 1.0, reject_finding)],
        final_stance="VETO",
        weighted_score=-1.0,
    )
    disagree_opinions = [
        AgentOpinion("quant_agent", "SUPPORT", 0.9, []),
        AgentOpinion("risk_officer", "SUPPORT", 1.0, []),
        AgentOpinion(
            "devils_advocate", "OPPOSE", 0.5, [Finding("THIN_EDGE_MARGIN", "ratio 1.2 < 1.5")]
        ),
        AgentOpinion("auditor_agent", "SUPPORT", 1.0, []),
    ]
    disagree_thesis = make_thesis(
        opinions=disagree_opinions, final_stance="NEUTRAL", weighted_score=0.1
    )

    return [
        generate_narrative("BTC-USDT", make_regime(), None, None, [], None),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            approve_decision(),
            approve_thesis.opinions,
            approve_thesis,
        ),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            reduce_decision(),
            reduce_thesis.opinions,
            reduce_thesis,
        ),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            reject_decision(),
            reject_thesis.opinions,
            reject_thesis,
        ),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            approve_decision(),
            disagree_opinions,
            disagree_thesis,
        ),
    ]


def test_disclaimer_present_in_every_branch(
    make_candidate, make_regime, approve_decision, reduce_decision, reject_decision, make_thesis
):
    for narrative in _all_branch_narratives(
        make_candidate, make_regime, approve_decision, reduce_decision, reject_decision, make_thesis
    ):
        assert DISCLAIMER in narrative


def test_denylist_never_appears(
    make_candidate, make_regime, approve_decision, reduce_decision, reject_decision, make_thesis
):
    for narrative in _all_branch_narratives(
        make_candidate, make_regime, approve_decision, reduce_decision, reject_decision, make_thesis
    ):
        lowered = narrative.lower()
        for banned in DENYLIST:
            assert banned not in lowered
