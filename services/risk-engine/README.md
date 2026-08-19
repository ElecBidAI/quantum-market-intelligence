# risk-engine

Phase 3: the mandatory gate (brief Section 9; docs/risk/RISK-GOVERNANCE.md).
`src/risk_engine/engine.py`'s `evaluate()` is the entire public surface — a pure
function, not a daemon: `(candidate, portfolio, market, limits) -> RiskDecision`.
It's called directly by whatever produces a candidate; there is no network
boundary yet because `services/strategy-engine` doesn't exist to call it (Phase 6).

`evaluate()` returns a dict shaped exactly like
[`packages/contracts/src/risk.ts`](../../packages/contracts/src/risk.ts)'s
`riskDecision` schema (camelCase keys: `decision`, `strategyId`, `reasons`,
`sizingAdjustment`, `timestamp`) even though it's Python, not TypeScript — same
rationale as `services/feature-engine`: no shared-type mechanism across the
language boundary in this repo, so the JSON shape itself is the contract.

Hard limits (`src/risk_engine/limits.py`) are conservative placeholders, not
researched values — see the module docstring. **Nobody should rely on the
defaults for anything beyond local testing.**

## What it checks

- Hard REJECT triggers (checked first, short-circuit): kill switch, circuit
  breaker, stale data, spread/liquidity limit, max daily/weekly loss, max
  portfolio drawdown, portfolio VaR (only when return history is supplied).
- Sizing caps, which can REDUCE instead of REJECT: max position, max asset
  exposure, max gross exposure, max leverage, max net exposure, and a
  per-trade risk budget computed via `quant_core.risk.fixed_fractional_size`.
  When multiple caps bind, the tightest wins and every triggered reason is
  reported.
- If every cap allows zero additional size, the result is REJECT — a
  `sizingAdjustment` of exactly 0 would look like "not evaluated yet" to a
  downstream consumer, so that case is a REJECT instead.

## Not in Phase 3

- **Max sector exposure** — no crypto sector taxonomy exists anywhere in this
  repository to check against.
- **Risk of ruin** — belongs to `services/simulation-engine` (brief Section 13
  lists it as a Monte Carlo *output*), not a closed-form formula here.
- Not wired into a live pipeline — there's no `services/strategy-engine`
  producing real candidates yet, and no `services/paper-execution` consuming
  approved/reduced ones. `evaluate()` is fully tested standalone so that
  wiring, when it happens, is "call this function," not "build this logic."
- No persistence — nothing here writes to the `risk_decisions` table yet
  (`data/migrations/0001_init.sql`). Whatever calls `evaluate()` is
  responsible for persisting the result once there's a real caller.

## Tests

`tests/test_engine.py` isolates each hard-reject trigger and each sizing cap
individually (via a deliberately wide-open `LOOSE_LIMITS` baseline, tightened
one field at a time), plus multi-cap interaction and short-direction sign
handling. `tests/test_state_and_limits.py` covers input validation.
