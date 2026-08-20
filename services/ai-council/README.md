# ai-council

Phase 8: analytical agents (brief Section 16). Agents analyze; none of them
execute — there is no code path here that can produce an order, only
`AgentOpinion`s.

**Deliberately rule-based, not LLM-backed.** Every agent is a pure function
over evidence the pipeline already produced (a `StrategyCandidate`, a
`RegimeResult`, a `risk_engine` decision) — no external API calls, no
non-determinism, no free-text generation. Brief Section 24 explicitly
forbids treating AI text output as a market signal; a rule-based council
that only ever emits structured stances and machine-readable findings
can't violate that by construction, the same way every other structural
gate in this repo (regime, no-look-ahead, risk isolation) works by
construction rather than convention.

## Agents implemented

- **`QuantAgent`** — audits the candidate's own claimed `expectedEdge`
  against its own claimed `estimatedCosts`. A high ratio means "internally
  consistent," not "actually profitable" — only a real backtest can claim
  that.
- **`RiskOfficer`** — its opinion *is* `risk_engine`'s decision, translated,
  never re-derived: `REJECT` -> `VETO`, `REDUCE` -> `NEUTRAL` (confidence
  reflecting how much was cut), `APPROVE` -> `SUPPORT`.
- **`DevilsAdvocate`** — structurally cannot output `SUPPORT`; `analyze()`
  only returns `OPPOSE` or `NEUTRAL`. Checks regime confidence, signal
  strength, edge-to-cost margin (a stricter threshold than `QuantAgent`'s),
  and historical win rate when a backtest summary is supplied.
- **`Auditor`** — checks for contradictions: does the candidate's stated
  regime still match the regime the council was actually given (catching a
  stale candidate evaluated too late), and do stop/target prices sit on the
  correct side of entry for the stated direction.
- **`council.synthesize()`** is the Chief Intelligence Agent: not a fifth
  analytical lens, a fixed aggregation rule. A single `VETO` (only
  `RiskOfficer` can produce one) makes the thesis `VETO` unconditionally —
  brief Section 16's "Risk Officer retains veto," enforced the same way
  `risk_engine`'s own hard-reject tier short-circuits everything after it.
  Otherwise the thesis is a confidence-weighted average of every stance, so
  a confident dissent outweighs a wishy-washy endorsement.

`tests/test_integration.py` runs the full chain — bars → regime → candidate
→ risk decision → council — including a case where a candidate's frozen
`regime` field no longer matches a freshly-reclassified regime, which
`Auditor` catches.

## Narrator

`narrator.py` (added after Phase 8, alongside the platform's separate
Access & Licensing work) renders the pipeline's structured output — a
`StrategyCandidate`, `RegimeResult`, risk decision, and the council's
`AgentOpinion`s/`ChiefIntelligenceThesis` — as plain-language, broker-voice
prose: "here's the regime, here's what the strategy proposed, here's what
risk management decided and why, here's whether the council agrees." It is
**explanatory, not a new decision authority**: it runs strictly *after*
`risk_engine.evaluate()` and `council.synthesize()` have already produced
their outputs, restates them, and cannot alter, delay, or bypass either.
No LLM call is involved — every sentence is a fixed template over fields
that already exist on its inputs, and every branch (including a hard
`REJECT`) ends with a fixed disclaimer (paper/simulated account only, not
investment advice, no capital at risk). See the module's own docstring for
the exact branch/wording rules, and `tests/test_narrator.py` for the
denylist/field-fidelity regression tests that guard against it ever
drifting into a profitability claim.

**Bilingual.** `generate_narrative(..., language="en" | "es")` renders both
languages from the exact same pipeline output — `run_pipeline.py` calls it
twice per symbol, never re-running the pipeline. Machine-generated
`reason`/`finding` `detail` strings (e.g. `"position would be 5.00%, limit
is 3.00%"`) are never translated in either language — only the prose
sentence around them is; regime/direction/stance enum values (e.g.
`BULLISH_TREND`) get a display-only Spanish lookup table inside the prose,
but the stored/transmitted values never change. `test_narrator.py` runs
every branch test in both languages, including a Spanish denylist.

## Pipeline

`run_pipeline.py` (`python -m ai_council.run_pipeline`, renamed from
`run_narrative.py` — its scope grew) is a one-shot batch job — same "not a
daemon" status as `feature_engine.main` — that runs `regime_engine` →
`strategy_engine` → `risk_engine` → this council → `narrator.py` against
real Postgres-ingested bars and persists **everything it produces**:

- `signals` / `risk_decisions` (`data/migrations/0001_init.sql`) — the raw
  candidate and its risk decision, correlated by `strategy_id` + an
  exactly-matching `timestamp` (deliberately passed into
  `risk_engine.evaluate(now=...)` so the two rows line up by construction —
  `risk_decisions` has no `symbol` column to join on directly).
- `council_narratives` (`data/migrations/0009_council_narratives.sql`, `0010`
  for the bilingual columns) — the narrator's output, as above.
- `paper_orders` / `fills` / `portfolio_snapshots`
  (`data/migrations/0006_paper_execution.sql`) — when a decision is
  APPROVE/REDUCE, `paper_execution.orders.create_order_from_decision` +
  `FillSimulator.simulate_fill` produce a simulated order/fill, exactly the
  same functions `paper_execution`'s own `test_integration.py` exercises
  against synthetic fixtures — this is the first time they run against the
  real chain instead. Positions are **replayed from the `fills` ledger on
  every run** (`paper_execution.positions.replay_positions`), never carried
  in memory between runs, so there's no drift to reconcile against.

This is the first thing in the repository that chains the full pipeline
against real ingested data rather than synthetic test fixtures.

**Known limitation, documented not silent**: every run that gets an
APPROVE/REDUCE creates a *new* paper order/fill — there's no
de-duplication against an already-open position for the same
strategy/symbol/direction. Acceptable for a manually-triggered demo
script nothing schedules yet; would need addressing before this ever runs
unattended on a cadence.

## Not in Phase 8

- **Trader, Market Structure, Macro, On-Chain, Derivatives, Portfolio, and
  Security/Fraud Agents** — each needs a data source or analytical
  capability this repository doesn't have yet (macro data, on-chain data,
  derivatives data, live microstructure metrics, a wired-up
  portfolio-engine, fraud/security detection). Implementing them as
  always-`NEUTRAL` stubs would be worse than not having them: a stub that
  always abstains looks identical to "checked and found nothing," which is
  a lie about what actually happened.
- **Not a live/scheduled service** — `run_pipeline.py` is a batch job, not
  a daemon; nothing in this repository schedules it (cron/systemd timer,
  same as `feature-engine`).

## Tests

69 tests. Every agent's confidence formula is checked against hand-picked
boundary values (e.g. `QuantAgent`'s edge/cost ratio at exactly its SUPPORT
threshold), not just "some opinion was returned." `test_narrator.py` and
`test_db.py` cover the narrator/pipeline persistence layer added after
Phase 8, including both languages.
