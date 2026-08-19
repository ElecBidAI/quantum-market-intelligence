# QMI — Risk Governance

Status: Phase 0. This document defines the risk governance policy the whole system
must obey. The Risk Engine itself is implemented starting Phase 3; until then, this
document is the binding policy even though no code enforces it yet.

## 1. Core rule

**No AI agent, signal, strategy, or model may bypass the Risk Engine.** A strategy
candidate (Section 6 of `DATA-CONTRACTS.md`) is never executable on its own. It only
becomes actionable after the Risk Engine emits a decision, and even then only
`APPROVE` or `REDUCE` allow it to proceed — `REJECT` is final for that candidate at
that point in time.

This rule applies uniformly to:

- rule-based strategies (`strategy-engine`)
- ML/statistical model output (`forecast-engine`, `regime-engine`)
- AI Council agent output (`ai-council`) — agents analyze, they never execute, and
  their conclusions carry no special authority to skip risk review
- manual/human-triggered candidates entered through any future UI

## 2. Decision contract

The Risk Engine returns exactly one of:

- `APPROVE` — candidate may proceed as sized.
- `REDUCE` — candidate may proceed only at a reduced size (`sizingAdjustment` in the
  decision record); the original size is rejected.
- `REJECT` — candidate does not proceed. It may be re-submitted later if the
  underlying conditions change (e.g., liquidity improves), but the prior rejection is
  never silently overridden.

Every decision carries machine-readable `reasons` (`code` + `detail`), never a bare
boolean. Downstream systems and the audit trail key off `code`.

## 3. Mandatory risk measures

The Risk Engine (Phase 3+) must compute, at minimum:

- historical/parametric VaR
- CVaR / Expected Shortfall
- maximum drawdown
- downside deviation
- Ulcer Index
- beta
- tracking error
- Information ratio
- Omega / tail ratios
- leverage / exposure
- concentration
- correlations
- liquidity risk
- event risk
- risk of ruin

## 4. Position sizing methods (available to the Risk/Portfolio layer)

- fixed fractional
- ATR-based
- volatility targeting
- fractional Kelly
- portfolio risk budgets

Sizing methods inform the `sizingAdjustment` on a `REDUCE` decision; they do not
bypass the APPROVE/REDUCE/REJECT gate.

## 5. Hard controls (circuit breakers)

The following are hard limits, not advisory heuristics. A breach forces `REJECT` (or,
for portfolio-wide breaches, a kill switch) regardless of how attractive the
statistical evidence for a candidate looks:

- max position (per asset)
- max asset exposure
- max sector exposure
- max gross exposure
- max net exposure
- max leverage
- max daily loss
- max weekly loss
- max portfolio drawdown
- liquidity/spread limits
- stale-data rejection (a candidate built on stale market data is rejected, not
  approved with a caveat)
- circuit breaker (temporary halt after abnormal conditions)
- global kill switch (manual, immediate halt of all new approvals)

## 6. Microstructure veto

Per the Market Microstructure Engine (Section 5 of the brief): **a statistically
attractive signal can still be rejected for insufficient liquidity or excessive
expected market impact.** Opportunity Score and statistical edge do not override
liquidity/impact checks; they are independent gates that both must pass.

## 7. Execution isolation

- Paper trading is the default and only mode until Phase 10.
- Execution (`services/execution`) is architecturally isolated from analysis
  (`ai-council`, `strategy-engine`, `forecast-engine`, `regime-engine`) — those
  services have no code path that can place an order, paper or real.
- `services/paper-execution` only accepts candidates that already carry an
  `APPROVE`/`REDUCE` risk decision; it does not re-derive or trust a candidate's own
  claimed edge. As of Phase 7 this is enforced in code, not just policy:
  `paper_execution.orders.create_order_from_decision` cannot construct an order from
  a `REJECT` decision (or from no decision at all) — it raises.
- Real-money execution (`services/execution`) does not exist as working code until
  Phase 10, and Phase 10 begins only after explicit human approval and all
  risk/security acceptance criteria pass (Section 22 of the brief).

## 8. Security & key management

- Paper trading by default.
- Execution service isolated from analytical services (network- and
  deployment-level, not just code-level, once execution exists).
- Secrets are encrypted at rest and never committed to source control (see
  `.env.example` for the documented-but-unset variable list).
- API keys follow least privilege; no-withdrawal keys are used wherever the exchange
  supports them.
- 2FA/RBAC on any system that can reach an execution capability.
- Audit log and reconciliation are mandatory before any capital is at risk, including
  paper capital, so that paper results are trustworthy evidence for a later real-money
  decision.
- The risk-decision log is immutable (append-only; corrections are new records that
  reference the original, not edits).
- Model registry: every model version used to produce a prediction that fed a
  strategy candidate is recorded and retrievable.
- Dataset/version provenance: every backtest/simulation records exactly which data
  snapshot it ran against.
- Model-drift monitoring exists before any model output is allowed to influence
  sizing beyond a fixed, pre-approved cap.

## 9. Backtesting/simulation discipline that feeds risk decisions

Risk sign-off on a strategy is only meaningful if the backtest behind it followed the
standard in Section 14 of the brief: pre-registered hypothesis, frozen
train/validation/out-of-sample split, realistic costs (fees/spread/slippage/latency),
walk-forward testing, parameter sensitivity, bootstrap/Monte Carlo trade sequences,
comparison against a simple baseline, tested economic significance, and a
multiple-testing adjustment (e.g., Deflated Sharpe) when many variants were tried.
Look-ahead bias, survivorship bias, data leakage, overfitting, and unrealistic fills
invalidate a backtest for risk sign-off purposes even if the headline Sharpe looks
good.

## 10. Status progression

Every researched idea moves through exactly these statuses, recorded in the Research
Notebook (`docs` + `research/experiments`, implemented starting Phase 4):

```
REJECTED | RESEARCH | PAPER | APPROVED
```

`APPROVED` still does not mean "trading real money" — it means the strategy is
eligible for real-capital consideration under Phase 10's separate human-approval
process. `APPROVED` in the notebook and Phase 10 go-live are two different gates.

## 11. What's actually enforceable by running code today

Through Phase 2, none of the above was enforceable by running code — there was no
Risk Engine, Strategy Engine, or execution service. Phase 3 added
`services/risk-engine`'s `evaluate()` (Sections 2, 3, 5, and 6 of this document are
now real, tested code, not just policy prose). Phase 6 added `services/strategy-engine`,
which finally produces a real `StrategyCandidate` and, via
`strategy_engine.risk_adapter.candidate_to_risk_request`, actually calls
`evaluate()` — see `services/strategy-engine/tests/test_integration.py` for the
proof: APPROVE, REJECT (kill switch), and REDUCE (oversized request) all exercised
end to end. Phase 7 added `services/paper-execution`, which finally consumes a risk
decision: `orders.create_order_from_decision` structurally cannot build an order
from a `REJECT`, and `services/paper-execution/tests/test_integration.py` runs the
complete chain — bars, regime, candidate, risk decision, paper order, simulated
fill, position — end to end. Phase 8 added `services/ai-council`: rule-based
analytical agents (Section 16's "Risk Officer retains veto" is now enforced in
code — `RiskOfficer`'s opinion is `risk_engine`'s decision itself, translated, and
`council.synthesize()` treats a single `VETO` as absolute, the same way
`risk_engine`'s own hard-reject tier short-circuits everything after it). Council
opinions are advisory analysis alongside the pipeline, exactly as this section
requires — they carry no authority to approve, reduce, or execute anything
`risk_engine` didn't already decide. What's still missing is a *live* pipeline:
nothing runs this on a schedule against ingested market data, and nothing yet
writes to the `risk_decisions` table (only `paper_orders`/`fills`/
`portfolio_snapshots` have persistence wired up so far). This document exists so
that:

1. Every later phase is built against a stable, agreed policy instead of inventing risk
   rules ad hoc per feature.
2. `packages/contracts` already encodes the `RiskDecision` shape (Section 7 of
   `DATA-CONTRACTS.md`), and `services/risk-engine.evaluate()` already returns exactly
   that shape, so nothing downstream can be wired up without going through it.
3. Reviewers have a checklist: any PR that lets a strategy/candidate/model output
   reach `paper-execution` or `execution` without passing through
   `risk_engine.evaluate()` is a policy violation, independent of how good the code
   otherwise looks.
