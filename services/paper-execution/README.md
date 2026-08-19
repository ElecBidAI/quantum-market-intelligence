# paper-execution

Phase 7: simulated order/fill engine (brief Section 7). Only accepts
risk-approved/reduced candidates — structurally, not by convention.

## Pieces

- **`orders.py`** — `create_order_from_decision()` is the isolation
  boundary: it is impossible to construct a `PaperOrder` from anything but
  an `APPROVE`/`REDUCE` `risk_engine` decision. A `REJECT` (or a missing
  decision entirely) raises. A `REDUCE` order's size is the requested size
  scaled by the decision's `sizingAdjustment`.
- **`fills.py`** — `FillSimulator` fills in full, immediately, at the
  market price offset by half the spread plus slippage. Same "no
  order-book-level fill simulation" simplification as `services/backtester`
  (see its README) and for the same reason: no continuous order-book-depth
  history exists yet to simulate against.
- **`positions.py`** — `PositionBook`: standard weighted-average-entry-price
  accounting (adding to a position averages the entry price; an opposite-
  direction fill closes and realizes PnL on the closed portion; a fill
  larger than the open position closes it and flips). Every closed portion
  appends a *fractional* return to `closed_trade_returns`, directly
  compatible with `backtester.metrics`. Also provides **reconciliation**
  (brief Section 19): `replay_positions()` rebuilds a book from scratch from
  the fill ledger, and `reconcile()` diffs that against a live,
  incrementally-maintained book — catching drift (a missed or duplicated
  fill application) rather than trusting the running state.
- **`analytics.py`** — `summarize_trades()` runs `backtester.metrics`
  (win rate, expectancy, payoff ratio, profit factor) on paper-traded
  results, so a paper-trading track record is directly comparable to the
  backtest that justified researching the strategy in the first place. A
  metric that's mathematically undefined for the current trade count (e.g.
  payoff ratio with no losing trades yet) is `None`, never a fabricated 0.
- **`persistence.py`** — writes to the three new tables in
  `data/migrations/0006_paper_execution.sql`: `paper_orders`, `fills`,
  `portfolio_snapshots`. No `positions` table — see that migration's
  comment for why storing derived state separately would just create a
  second thing that could drift, which `reconcile()` already exists to
  catch for the in-memory case.

`tests/test_integration.py` extends `services/strategy-engine`'s
integration test all the way through: bars → regime → candidate → risk
decision → paper order → simulated fill → position, and confirms a
`REJECT` decision never reaches a fill.

## Not in Phase 7

- **Not a live/scheduled service.** Nothing runs this against live-ingested
  market data or a running risk-engine pipeline yet — it's a callable
  pipeline, proven by tests, same status as every `*-engine` service so far.
- **Partial fills / capacity constraints** — see `fills.py`'s docstring.
- **Multi-currency / margin / funding accounting** — spot-only,
  single-collateral-currency position tracking; no leverage, liquidation,
  or funding-rate mechanics (those need Phase 9's derivatives work first).

## Tests

32 tests. The position-book lifecycle (open, add, partial close, flip) is
checked against a fully hand-traced scenario (see the commit history for
the reference trace), not just "some position exists."
