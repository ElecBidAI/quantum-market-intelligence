# market-data

Phase 1: implemented for one exchange (Binance spot, public market-data streams
only — no API key, no order placement).

Ingests BTC-USDT and ETH-USDT (`src/symbols.ts`) over a single combined WebSocket
connection: trades (`@trade`), closed 1-minute bars (`@kline_1m`), and top-20 book
snapshots (`@depth20@100ms`). Every message is parsed into the shared
`@qmi/contracts` shape, run through the data-quality gates in `src/quality.ts`
(docs/architecture/DATA-CONTRACTS.md Section 8), persisted to Postgres
(`data/migrations/0002_market_data.sql`), and — if not rejected — published to
Redis for `apps/api`'s live SSE stream.

`src/exchange-adapter.ts` defines the common interface a second exchange adapter
would implement; nothing outside this service talks to Binance directly (see
docs/architecture/QMI-MASTER-ARCHITECTURE.md Section 5).

## Not in Phase 1

- Full incremental order-book reconstruction from diff/delta streams
  (`orderbook_deltas`, with sequence-gap detection) — the partial-depth snapshot
  stream used here already sends the full top-N book each update, so delta
  reconstruction is deferred until a strategy actually needs deeper/more precise
  book state.
- Additional exchanges, derivatives streams, or the remaining ~20 assets in the
  target universe.
- Any code path that can place an order — this service is read-only ingestion.

## Running locally

```bash
docker compose up -d          # Postgres/TimescaleDB + Redis
# apply data/migrations/0001_init.sql and 0002_market_data.sql
pnpm --filter @qmi/market-data dev
```

## Tests

`test/binance-parsers.test.ts`, `test/quality.test.ts`, `test/reconnect.test.ts`,
`test/binance-adapter.test.ts` (malformed-message and reconnect-with-backoff
behavior via a fake WebSocket — no real network in tests), `test/symbols.test.ts`.
