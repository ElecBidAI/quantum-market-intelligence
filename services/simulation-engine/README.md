# simulation-engine

Phase 5: Monte Carlo, bootstrap, and stress testing (brief Section 13).

Two independent pieces:

- **`monte_carlo.py`** — trade-sequence Monte Carlo. Takes historical/backtested
  trade returns (e.g. `backtester.engine.BacktestResult.round_trip_trade_returns`)
  and bootstrap-resamples many alternate sequences from them
  (`quant_core.simulation.iid_bootstrap_paths`), then reports every output the
  brief asks for: terminal-equity percentiles, probability of loss, probability
  of drawdown exceeding a threshold, expected shortfall, recovery-time
  distribution, longest-loss-streak distribution, and probability of ruin.
  `run_trade_sequence_monte_carlo()` runs the whole suite in one call.
- **`stress.py`** — the *quantifiable* stress scenarios from brief Section 13:
  price shocks (-10/-20/-40%), volatility multipliers (x2/x3), and a
  spread/cost multiplier (x5/x10) applied to `backtester.costs.TransactionCostModel`.

The lower-level path/return generators (GBM, jump diffusion, Student-t,
iid/block/regime-conditioned bootstrap) live in
[`packages/quant-core/src/quant_core/simulation.py`](../../packages/quant-core/src/quant_core/simulation.py) —
this service is a consumer of that library, the same split as
feature-engine/backtester vs. quant-core generally.

`ExperimentRecord`'s (`services/backtester`) `monte_carlo_summary` and
`stress_test_summary` fields can now actually be populated with this
service's output — they existed since Phase 4 as `None` placeholders because
nothing produced them yet.

## Not in Phase 5

- **Narrative stress scenarios**: exchange outage, extreme funding,
  liquidation cascade, correlation convergence, stablecoin depeg,
  hack/regulatory event. Each needs data or a model this repository doesn't
  have yet (leverage/liquidation data for cascades, a live multi-asset
  covariance estimator for correlation convergence, ...) — see the module
  docstring in `stress.py` for the full reasoning per scenario. Treating any
  of these as "multiply something by a number" would misrepresent what
  actually happens, so they're left as documented gaps instead.
- **Price-path Monte Carlo through the backtester** (i.e. running
  `backtester.engine.run_backtest` against many `quant_core.simulation`-generated
  paths to get a strategy-level PnL distribution, rather than resampling
  already-realized trades). Both pieces exist; nothing wires them together
  yet because there's no real strategy to run through it (Phase 6).
- **Parameter/cost sensitivity** (brief Section 13's last output) — running
  the same Monte Carlo across a grid of parameters/costs is a thin loop over
  `run_trade_sequence_monte_carlo` a caller can already write; no dedicated
  sweep utility exists yet since there's no real parameter grid to sweep.

## Tests

`test_monte_carlo.py`'s core assertions use a fully hand-traced two-path,
four-trade fixture (every number — terminal multiplier, drawdown, recovery
time, loss streak — computed independently and checked in the commit
history) rather than only structural/statistical checks. `test_stress.py`
and `test_persistence.py` follow the same known-value-first pattern used
throughout this repo.
