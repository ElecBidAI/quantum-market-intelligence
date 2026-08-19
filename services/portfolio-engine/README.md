# portfolio-engine

Not implemented as a separate service.

The allocation formulas this service was expected to own (brief Section 10:
expected return, variance, minimum-variance and max-Sharpe weights, risk
parity, diversification ratio, marginal/component risk contribution) were
implemented in Phase 3, but as part of
[`packages/quant-core/src/quant_core/portfolio.py`](../../packages/quant-core/src/quant_core/portfolio.py)
rather than a standalone service — same rationale as `services/feature-engine`
and `services/statistical-engine`: a service needs a live consumer feeding it
real inputs, and there's no forecast-engine yet to supply expected returns
(`mu`) or a live covariance estimator. quant-core's portfolio functions are
tested against synthetic inputs; they become a real service once something
produces `mu`/`Sigma` from actual market data and needs allocation decisions
on a schedule.

`min_variance_weights` and `max_sharpe_weights` are the **unconstrained**
closed-form solutions (can go short, can leverage) — long-only /
turnover-constrained optimization needs a quadratic-program solver, deferred
until a consumer needs constrained weights specifically.

## Not in Phase 3

- **Black-Litterman** and **Hierarchical Risk Parity** — both need
  materially more machinery (a view/uncertainty specification and prior for
  Black-Litterman; hierarchical clustering and quasi-diagonalization for
  HRP) than the closed-form/iterative methods implemented so far. See the
  module docstring in `packages/quant-core/src/quant_core/portfolio.py`.
- Transaction-cost and turnover constraints (brief Section 10) — need a
  constrained optimizer, same as long-only weights above.

See [`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](../../docs/architecture/QMI-MASTER-ARCHITECTURE.md)
for how this fits into the overall pipeline, and
[`docs/risk/RISK-GOVERNANCE.md`](../../docs/risk/RISK-GOVERNANCE.md) for the risk
rules it must obey once implemented.
