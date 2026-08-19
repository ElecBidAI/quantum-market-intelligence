# backtester

Phase 4: event-driven, single-asset backtesting (brief Section 14).

`src/backtester/engine.py`'s `run_backtest()` is the core: given a bar series
and a `strategy_fn(bars) -> position in [-1, 1]`, it walks forward one bar at
a time, calling `strategy_fn` with only `bars[:t+1]` at step `t` — the
no-look-ahead guarantee is structural, not a convention the strategy has to
remember. Costs (`src/backtester/costs.py`) are a single proportional rate
(fee + slippage + spread bps) charged on turnover whenever the position
changes. `src/backtester/metrics.py` computes the standard performance suite
(Sharpe/Sortino/Calmar, win rate/expectancy/payoff ratio/profit factor,
turnover), reusing `quant_core.risk` for drawdown/downside-deviation math.
`src/backtester/walk_forward.py` splits a bar series into rolling
train/test windows. `src/backtester/experiment.py` +
`src/backtester/persistence.py` record a reproducible experiment
(brief Section 17) into `data/migrations/0004_backtests.sql`'s
`backtests`/`research_runs` tables.

## Not in Phase 4

- **Partial fills / order-book-level execution.** Every trade fills in full
  at the bar's close-to-close return; there's no capacity constraint. A real
  fill simulator needs a continuous order-book-depth history, which Phase 1
  doesn't ingest yet (see `services/market-data/README.md`).
- **The full Deflated Sharpe Ratio.** `metrics.py` offers
  `sharpe_significance_pvalue` + `bonferroni_adjusted_pvalue` instead — a
  plainer, more conservative multiple-testing correction. The actual DSR
  formula (Bailey & Lopez de Prado) has skewness/kurtosis correction terms
  that are easy to misstate without a verified reference to check against;
  see the module docstring.
- **Capacity.** Needs a market-impact model (microstructure-engine, not
  implemented).
- **Multi-asset / portfolio backtesting.** `run_backtest` is single-symbol;
  combining several via `quant_core.portfolio` is possible by hand today,
  but nothing orchestrates it.
- **Monte Carlo / bootstrap trade sequences and stress testing**
  (brief Section 14, steps 6-7) — that's `services/simulation-engine`,
  Phase 5. `ExperimentRecord`'s `monte_carlo_summary` and
  `stress_test_summary` fields exist now and default to `None` so the
  record's shape doesn't change when Phase 5 fills them in.

## Tests

Every numeric function is tested against a value computed independently
(not just re-derived by hand) — see the commit history for the reference
scripts. `test_engine.py` additionally verifies the no-look-ahead property
directly (recording exactly how much of the bar series `strategy_fn` was
given at each step) and that two runs of the same backtest are byte-for-byte
identical (brief Section 21: "deterministic replay").
