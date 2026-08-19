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

## Not in Phase 8

- **Trader, Market Structure, Macro, On-Chain, Derivatives, Portfolio, and
  Security/Fraud Agents** — each needs a data source or analytical
  capability this repository doesn't have yet (macro data, on-chain data,
  derivatives data, live microstructure metrics, a wired-up
  portfolio-engine, fraud/security detection). Implementing them as
  always-`NEUTRAL` stubs would be worse than not having them: a stub that
  always abstains looks identical to "checked and found nothing," which is
  a lie about what actually happened.
- **No persistence.** The brief's Section 20 database-domain list has no
  council-decisions table, and inventing one wasn't asked for — a council
  thesis is meant to inform the same audit trail `research_runs` and
  `risk_decisions` already provide, not become a new source of truth.
- **Not a live/scheduled service** — same status as every other
  `*-engine`/`*-council` component so far: a callable pipeline, proven by
  tests, not a daemon.

## Tests

36 tests. Every agent's confidence formula is checked against hand-picked
boundary values (e.g. `QuantAgent`'s edge/cost ratio at exactly its SUPPORT
threshold), not just "some opinion was returned."
