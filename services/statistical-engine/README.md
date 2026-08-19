# statistical-engine

Not implemented as a separate service.

The descriptive/inferential statistics formulas this service was expected to
own (`packages/quant-core/src/quant_core/stats.py`: mean/median/variance,
MAD/IQR, skewness/kurtosis, Pearson/Spearman/Kendall correlation,
rolling/partial correlation, autocorrelation, confidence intervals) were
implemented in Phase 2, but as part of `packages/quant-core` and consumed
directly by `services/feature-engine` rather than run as their own service —
see `services/feature-engine/README.md` for why. This directory becomes a
real service only if a reason emerges to run these computations
independently of feature-engine (e.g. a different latency/scaling profile,
or a consumer that isn't feature-engine).

Formal hypothesis tests that need a distribution CDF beyond the normal
(t-tests, chi-square, Kolmogorov-Smirnov) and econometric tests that need
critical-value tables (ADF/KPSS, Engle-Granger/Johansen cointegration) are
not implemented anywhere yet — see the module docstring in
`packages/quant-core/src/quant_core/stats.py` for why they're deferred.

See [`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](../../docs/architecture/QMI-MASTER-ARCHITECTURE.md)
for how this fits into the overall pipeline, and
[`docs/risk/RISK-GOVERNANCE.md`](../../docs/risk/RISK-GOVERNANCE.md) for the risk
rules it must obey once implemented.
