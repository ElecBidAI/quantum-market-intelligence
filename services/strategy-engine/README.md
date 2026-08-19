# strategy-engine

Phase 6: pluggable strategy candidate generation (brief Section 8) — and the
first point in this repository where a candidate actually reaches
`risk_engine.evaluate()` (Phase 3's mandatory gate, unwired until now).

## Pieces

- **`strategy.py`** — `Strategy` (a `Protocol`: `strategy_id`,
  `allowed_regimes`, `generate()`) and `StrategyCandidate`, mirroring
  `packages/contracts/src/strategy.ts`'s `strategyCandidate` schema
  field-for-field. A candidate is never an executable order.
- **`strategies/`** — three concrete strategies, one per family, each
  declaring which regimes it's allowed to operate in:
  - `TrendFollowingStrategy` (SMA crossover) — `BULLISH_TREND`/`BEARISH_TREND`
  - `MeanReversionStrategy` (Bollinger Band) — `SIDEWAYS`/`LOW_VOLATILITY`
  - `BreakoutStrategy` (Donchian channel, using the *prior* channel so it's
    not self-referential) — `HIGH_VOLATILITY`/`BULLISH_TREND`/`BEARISH_TREND`
- **`engine.py`** — `run_strategies()` enforces the regime gate
  *structurally*: a strategy's `generate()` is never even called for a
  regime outside its `allowed_regimes`, the same "don't trust self-policing"
  pattern `risk_engine` and `backtester` use.
- **`scoring.py`** — the QMI transparent scores (brief Section 15):
  `opportunity_score`, `risk_score`, `confidence_score` (all a generic,
  caller-supplied-components weighted average — see the module docstring for
  why nothing is hard-coded), and `net_edge_score` (the brief's own formula,
  verbatim: `Opportunity x (1 - Risk/100) x (Confidence/100)`).
- **`risk_adapter.py`** — `candidate_to_risk_request()` converts a
  `StrategyCandidate` into `risk_engine.state.CandidateRequest`, deriving
  `stop_distance_pct` from the candidate's own `entryLogic`/`stopLogic`
  prices. This is the missing link: Phase 3 built the gate, Phase 6 finally
  produces something real to send through it.
- **`persistence.py`** — writes into the `signals` table, which has existed
  since Phase 0 (`data/migrations/0001_init.sql`) waiting for a producer.

`test_integration.py` runs the whole thing end to end: synthetic bars ->
`classify_regime()` -> `run_strategies()` -> `candidate_to_risk_request()`
-> `risk_engine.evaluate()`, checking APPROVE, REJECT (kill switch), and
REDUCE (oversized request) all actually happen.

## Not in Phase 6

- **The other ~13 strategy families** the brief lists (pairs trading,
  statistical/cross-exchange/triangular arbitrage, spot/futures basis,
  funding arbitrage, sector rotation, options-volatility, scalping,
  intraday/swing/position variants) — each needs infrastructure this repo
  doesn't have yet (multi-exchange data, derivatives data, a sector
  taxonomy, options data). Three strategies across three different families
  is enough to prove the pluggable-interface pattern; adding the rest before
  there's data to back them would be exactly the "dozens of indicators
  before the foundation is correct" the brief warns against (Section 24).
- **Backtested `expectedEdge`.** Every strategy's `expectedEdge` is a naive
  placeholder (a spread/width ratio), not a number derived from actually
  running the strategy through `services/backtester` — see each strategy's
  module docstring.
- **Not a live/scheduled service.** Nothing runs `run_strategies()` against
  live ingested data on a schedule yet; it's a callable pipeline, proven by
  the integration tests, not a daemon.

## Tests

Every strategy is exercised against a fixture whose exact numeric output
(band values, ATR-derived stop, expected edge, ...) was computed once via a
reference script and hardcoded as the expected value — not just "a candidate
was returned." 37 tests total across strategies, scoring, the regime gate,
the risk adapter, persistence, and the end-to-end integration.
