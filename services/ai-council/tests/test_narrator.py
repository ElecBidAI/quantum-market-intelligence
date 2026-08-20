import pytest

from ai_council.narrator import DISCLAIMER_EN, DISCLAIMER_ES, generate_narrative
from ai_council.opinion import AgentOpinion, Finding

DENYLIST_EN = ["guaranteed", "will profit", "buy now", "can't lose", "sure thing", "moon"]
DENYLIST_ES = [
    "garantizado",
    "ganancia asegurada",
    "no puedes perder",
    "compra ahora",
    "algo seguro",
    "a la luna",
]

LANGUAGES = ["en", "es"]


def disclaimer_for(language: str) -> str:
    return DISCLAIMER_ES if language == "es" else DISCLAIMER_EN


def denylist_for(language: str) -> list[str]:
    return DENYLIST_ES if language == "es" else DENYLIST_EN


@pytest.mark.parametrize("language", LANGUAGES)
def test_no_candidate_branch(make_regime, language):
    regime = make_regime(label="SIDEWAYS", confidence=0.6)
    narrative = generate_narrative("BTC-USDT", regime, None, None, [], None, language=language)

    if language == "es":
        assert "Ninguna de las tres" in narrative
        assert "lateral" in narrative
    else:
        assert "None of the three strategies" in narrative
        assert "SIDEWAYS" in narrative
    assert disclaimer_for(language) in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_multi_candidate_disclosure(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
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
        language=language,
    )
    if language == "es":
        assert "3 estrategias generaron candidatos" in narrative
        assert "seleccionado por tener el mayor margen esperado (0.0800)" in narrative
    else:
        assert "3 strategies generated candidates" in narrative
        assert "selected because it had the highest expected edge (0.0800)" in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_multi_candidate_disclosure_when_selection_used_a_real_backtested_sharpe(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
    candidate = make_candidate(expectedEdge=0.01)  # low self-reported edge, doesn't matter here
    thesis = make_thesis()
    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        candidate,
        approve_decision(),
        thesis.opinions,
        thesis,
        candidate_pool_size=3,
        backtested_sharpe=1.75,
        language=language,
    )
    if language == "es":
        assert "mejor desempeño real en backtesting" in narrative
        assert "Sharpe 1.75" in narrative
        assert "seleccionado por tener el mayor margen esperado" not in narrative
    else:
        assert "best real backtested track record" in narrative
        assert "Sharpe 1.75" in narrative
        assert "selected because it had the highest expected edge" not in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_reject_branch(make_candidate, make_regime, reject_decision, make_thesis, language):
    decision = reject_decision()
    reason = decision["reasons"][0]
    veto_officer = AgentOpinion(
        "risk_officer", "VETO", 1.0, [Finding(reason["code"], reason["detail"])]
    )
    thesis = make_thesis(opinions=[veto_officer], final_stance="VETO", weighted_score=-1.0)

    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        make_candidate(),
        decision,
        thesis.opinions,
        thesis,
        language=language,
    )

    assert "breached" in narrative  # reason detail is never translated
    if language == "es":
        assert "Yo pasaría de esta" in narrative
        assert "el límite de pérdida diaria ya se superó" in narrative
        assert "los agentes analíticos no tienen una opinión aparte aquí" in narrative
    else:
        assert "I'd pass on this one" in narrative
        assert "the day's loss limit is already breached" in narrative
        assert "the analytical agents don't get a separate say here" in narrative
    assert disclaimer_for(language) in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_reduce_branch(make_candidate, make_regime, reduce_decision, make_thesis, language):
    decision = reduce_decision(adjustment=0.5)
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        make_candidate(),
        decision,
        thesis.opinions,
        thesis,
        language=language,
    )

    assert "capped" in narrative  # reason detail is never translated
    if language == "es":
        assert "se redujo a 50%" in narrative
        assert "el límite de tamaño de posición para este activo (capped)" in narrative
        assert "respondieron" in narrative  # council summary sentence
    else:
        assert "cut to 50%" in narrative
        assert "the position size limit for this asset (capped)" in narrative
        assert "came back" in narrative  # council summary sentence
    assert disclaimer_for(language) in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_approve_support_branch(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
    thesis = make_thesis(final_stance="SUPPORT", weighted_score=1.0)

    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        make_candidate(),
        approve_decision(),
        thesis.opinions,
        thesis,
        language=language,
    )

    if language == "es":
        assert "La gestión de riesgo la aprobó al tamaño completo solicitado" in narrative
        assert "Ningún límite se activó" in narrative
        assert "no es una lectura del todo limpia" not in narrative
    else:
        assert "Risk management cleared this at full requested size" in narrative
        assert "No limits were binding" in narrative
        assert "isn't a clean read internally" not in narrative
    assert disclaimer_for(language) in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_approve_disagreement_branch(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
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
        "BTC-USDT",
        make_regime(),
        make_candidate(),
        approve_decision(),
        opinions,
        thesis,
        language=language,
    )

    assert "ratio 1.20 < 1.5" in narrative  # finding detail is never translated
    if language == "es":
        assert "La gestión de riesgo la aprobó al tamaño completo solicitado" in narrative
        assert "no es una lectura del todo limpia" in narrative
        assert "el margen sobre los costos se ve escaso" in narrative
        assert "no como razón para anular la decisión de riesgo" in narrative
    else:
        assert "Risk management cleared this at full requested size" in narrative
        assert "isn't a clean read internally" in narrative
        assert "the edge over costs looks thin" in narrative
        assert "not a reason to override risk's decision" in narrative
    assert disclaimer_for(language) in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_missing_entry_stop_target_prices(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
    candidate = make_candidate(entryLogic={}, stopLogic={}, targetLogic={})
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        candidate,
        approve_decision(),
        thesis.opinions,
        thesis,
        language=language,
    )

    if language == "es":
        assert "no definió precios explícitos de entrada/stop/objetivo" in narrative
    else:
        assert "didn't populate explicit entry/stop/target prices" in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_present_entry_stop_target_prices_are_not_invented(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
    candidate = make_candidate(
        entryLogic={"entryPrice": 100.0},
        stopLogic={"stopPrice": 95.0},
        targetLogic={"targetPrice": 110.0},
    )
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        candidate,
        approve_decision(),
        thesis.opinions,
        thesis,
        language=language,
    )

    if language == "es":
        assert "entrada alrededor de 100.0" in narrative
        assert "un stop en 95.0" in narrative
        assert "un objetivo en 110.0" in narrative
    else:
        assert "entry around 100.0" in narrative
        assert "a stop at 95.0" in narrative
        assert "a target at 110.0" in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_expected_edge_and_costs_are_not_invented(
    make_candidate, make_regime, approve_decision, make_thesis, language
):
    candidate = make_candidate(expectedEdge=0.0512, estimatedCosts=0.0099)
    thesis = make_thesis()

    narrative = generate_narrative(
        "BTC-USDT",
        make_regime(),
        candidate,
        approve_decision(),
        thesis.opinions,
        thesis,
        language=language,
    )

    assert "0.0512" in narrative
    assert "0.0099" in narrative
    if language == "es":
        assert "no un pronóstico de ganancias validado" in narrative
    else:
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
    make_candidate,
    make_regime,
    approve_decision,
    reduce_decision,
    reject_decision,
    make_thesis,
    language,
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
        generate_narrative("BTC-USDT", make_regime(), None, None, [], None, language=language),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            approve_decision(),
            approve_thesis.opinions,
            approve_thesis,
            language=language,
        ),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            reduce_decision(),
            reduce_thesis.opinions,
            reduce_thesis,
            language=language,
        ),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            reject_decision(),
            reject_thesis.opinions,
            reject_thesis,
            language=language,
        ),
        generate_narrative(
            "BTC-USDT",
            make_regime(),
            make_candidate(),
            approve_decision(),
            disagree_opinions,
            disagree_thesis,
            language=language,
        ),
    ]


@pytest.mark.parametrize("language", LANGUAGES)
def test_disclaimer_present_in_every_branch(
    make_candidate,
    make_regime,
    approve_decision,
    reduce_decision,
    reject_decision,
    make_thesis,
    language,
):
    narratives = _all_branch_narratives(
        make_candidate,
        make_regime,
        approve_decision,
        reduce_decision,
        reject_decision,
        make_thesis,
        language,
    )
    for narrative in narratives:
        assert disclaimer_for(language) in narrative


@pytest.mark.parametrize("language", LANGUAGES)
def test_denylist_never_appears(
    make_candidate,
    make_regime,
    approve_decision,
    reduce_decision,
    reject_decision,
    make_thesis,
    language,
):
    narratives = _all_branch_narratives(
        make_candidate,
        make_regime,
        approve_decision,
        reduce_decision,
        reject_decision,
        make_thesis,
        language,
    )
    for narrative in narratives:
        lowered = narrative.lower()
        for banned in denylist_for(language):
            assert banned not in lowered
