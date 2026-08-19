# market-data

Phase 1 (spot) and Phase 9 (perpetual futures), both Binance-only, both
public market-data streams only — no API key, no order placement.

Ingests BTC-USDT and ETH-USDT (`src/symbols.ts`) over a single combined spot
WebSocket connection: trades (`@trade`), closed 1-minute bars (`@kline_1m`), and
top-20 book snapshots (`@depth20@100ms`). Separately, `BinanceFuturesAdapter`
(`src/adapters/binance-futures.ts`) connects to the USDT-M futures WebSocket and
ingests funding rate and futures-vs-index basis from the `@markPrice@1s` stream.
Every message is parsed into the shared `@qmi/contracts` shape, run through the
data-quality gates in `src/quality.ts` (docs/architecture/DATA-CONTRACTS.md
Section 8), persisted to Postgres (`data/migrations/0002_market_data.sql` for
spot, `data/migrations/0007_derivatives.sql` for futures), and — if not rejected
— published to Redis for `apps/api`'s live SSE stream.

`src/exchange-adapter.ts` defines the common interface a second spot exchange
adapter would implement; nothing outside this service talks to Binance directly
(see docs/architecture/QMI-MASTER-ARCHITECTURE.md Section 5).
`BinanceFuturesAdapter` deliberately does not implement that interface — funding
rate/basis don't fit the trade/OHLCV/order-book shape spot adapters share.

## Not in Phase 1 / Phase 9

- Full incremental order-book reconstruction from diff/delta streams
  (`orderbook_deltas`, with sequence-gap detection) — the partial-depth snapshot
  stream used here already sends the full top-N book each update, so delta
  reconstruction is deferred until a strategy actually needs deeper/more precise
  book state.
- Open interest: Binance only exposes it via REST poll
  (`GET /fapi/v1/openInterest`), and this service is WebSocket-push only —
  deferred until a real consumer needs it and justifies adding a polling loop.
- Liquidation events: requires the separate `@forceOrder` stream, not yet wired.
- Options data (Greeks, IV, smile/skew) — out of scope per the brief's own
  "options later" phrasing; see `quant_core.derivatives` module docstring.
- Additional exchanges, or the remaining ~20 assets in the target universe.
- Any code path that can place an order — this service is read-only ingestion.

## Running locally

```bash
docker compose up -d          # Postgres/TimescaleDB + Redis
# apply data/migrations/0001_init.sql through 0007_derivatives.sql
pnpm --filter @qmi/market-data dev
```

## Tests

`test/binance-parsers.test.ts`, `test/quality.test.ts`, `test/reconnect.test.ts`,
`test/binance-adapter.test.ts` (malformed-message and reconnect-with-backoff
behavior via a fake WebSocket — no real network in tests), `test/symbols.test.ts`,
`test/binance-futures-parsers.test.ts`, `test/binance-futures-adapter.test.ts`.
