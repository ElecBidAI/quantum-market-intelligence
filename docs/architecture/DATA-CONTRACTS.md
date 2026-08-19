# QMI — Data Contracts

Status: Phase 0. This document is the canonical description of QMI's data shapes.
The executable source of truth is `packages/contracts` (TypeScript/zod); this document
must stay in sync with it. When they disagree, the code in `packages/contracts` wins
and this document is stale and should be fixed.

## 1. Principles

- Every record that originates outside our own computation carries provenance:
  `source`, `exchange` (venue), `symbol`, `timestamp` (event time, UTC), `ingestedAt`
  (UTC), `qualityStatus`, and `schemaVersion`.
- Timestamps are always UTC, always explicit (ISO 8601 with `Z`, or epoch millis —
  `packages/contracts` uses ISO 8601 strings internally and documents the choice at
  each schema).
- Nothing in these contracts implies a value is safe to trade on. Quality gates are a
  separate concern (Section 5) applied on top of raw ingested data.
- Contracts are additive-evolution first: new optional fields are cheap, breaking
  changes bump `schemaVersion` and require a migration note in this document.

## 2. Common envelope

Every market/derivatives/context record embeds:

| Field           | Type                              | Notes                                   |
|-----------------|------------------------------------|------------------------------------------|
| `source`        | string                             | ingestion pipeline / vendor id           |
| `exchange`      | string                             | venue identifier, e.g. `"binance"`       |
| `symbol`        | string                             | normalized symbol, e.g. `"BTC-USDT"`     |
| `timestamp`     | string (ISO 8601 UTC)              | venue/event time                         |
| `ingestedAt`    | string (ISO 8601 UTC)              | time our system received/persisted it    |
| `qualityStatus` | `"ok" \| "suspect" \| "rejected"`  | set by data-quality gates                |
| `schemaVersion` | integer                            | contract version for this record type    |

## 3. Market data

### 3.1 Trade / tick

```ts
{
  ...envelope,
  price: number,
  size: number,
  side: "buy" | "sell" | "unknown",
  tradeId: string,
}
```

### 3.2 OHLCV (bar)

```ts
{
  ...envelope,
  interval: string,   // e.g. "1m", "5m", "1h", "1d"
  open: number,
  high: number,
  low: number,
  close: number,
  volume: number,
}
```

### 3.3 Best bid/ask (quote)

```ts
{
  ...envelope,
  bidPrice: number,
  bidSize: number,
  askPrice: number,
  askSize: number,
}
```

### 3.4 Order-book snapshot

```ts
{
  ...envelope,
  bids: Array<[price: number, size: number]>,
  asks: Array<[price: number, size: number]>,
  sequenceId: number,
}
```

### 3.5 Order-book delta

```ts
{
  ...envelope,
  side: "bid" | "ask",
  price: number,
  size: number,        // 0 means "remove this level"
  sequenceId: number,
  previousSequenceId: number,
}
```

Consumers must verify `previousSequenceId` chains without gaps; a gap means the local
book must be rebuilt from a fresh snapshot, not silently patched.

## 4. Derivatives (Phase 9, schemas reserved now)

- **Funding rate**: `{ ...envelope, rate: number, intervalHours: number }`
- **Open interest**: `{ ...envelope, openInterest: number, notional: number }`
- **Basis**: `{ ...envelope, spotPrice: number, futuresPrice: number, basis: number, annualizedBasis: number }`
- **Liquidation event**: `{ ...envelope, side: "long" | "short", price: number, size: number }`
- **Futures curve point**: `{ ...envelope, expiry: string, price: number }`
- Options IV/skew/Greeks: reserved, not defined until the options phase.

These are documented here so the shapes are planned, but they are not implemented in
`packages/contracts` until the Derivatives Engine phase; adding them early without a
consumer would be speculative.

## 5. Context data (schemas reserved)

On-chain metrics, tokenomics/unlocks, macro events, news/event risk, and
protocol/security events are documented as future contract families. They are not
defined in code in Phase 0 — there is no ingestion pipeline yet to produce them, and a
schema without a producer or consumer tends to drift from reality.

## 6. Strategy candidate (defined now, per Section 8 of the brief)

```ts
{
  strategyId: string,
  symbol: string,
  venue: string,
  direction: "LONG" | "SHORT" | "NEUTRAL",
  horizon: string,
  signalStrength: number,
  entryLogic: Record<string, unknown>,
  invalidationLogic: Record<string, unknown>,
  stopLogic: Record<string, unknown>,
  targetLogic: Record<string, unknown>,
  expectedEdge: number,
  estimatedCosts: number,
  regime: string,
  timestamp: string, // ISO 8601 UTC
}
```

This object is a **candidate**. It is never an executable order. It only becomes
actionable after `risk-engine` returns `APPROVE` or `REDUCE`.

## 7. Risk decision (defined now, per Section 9 of the brief)

```ts
{
  decision: "APPROVE" | "REDUCE" | "REJECT",
  strategyId: string,
  reasons: Array<{ code: string, detail: string }>,
  sizingAdjustment: number | null, // present when decision === "REDUCE"
  timestamp: string, // ISO 8601 UTC
}
```

`reasons` is always machine-readable (`code`) plus a human-readable `detail`; UI and
audit logging both read `code`, never parse `detail`.

## 8. Data-quality gates

Applied before a record's `qualityStatus` is set to `"ok"`:

- missing intervals (gap detection against expected bar cadence)
- stale feeds (no update within an expected max age)
- crossed books (`bestBid >= bestAsk`)
- abnormal timestamps (future timestamps, timestamps far behind wall clock)
- duplicate ticks (same `tradeId`/`sequenceId` seen twice)
- outliers (price/size far outside a rolling robust range)
- exchange disconnects (gap in the sequence tied to a known disconnect event)

**Rule: failing a gate never triggers silent imputation of critical live trading
data.** A record that fails a gate is marked `"suspect"` or `"rejected"` and carries
that status downstream; it is not corrected and re-labeled `"ok"` automatically.

`services/market-data/src/quality.ts` (Phase 1) implements crossed books, stale
feeds, abnormal (future) timestamps, and duplicate ticks. Missing-interval detection,
outlier detection, and exchange-disconnect detection are not implemented yet — they
need a baseline of real ingested data to define "expected cadence" and "abnormal"
against, which Phase 1 is what starts producing.

## 9. Database domains (target, Section 20 of the brief)

`market_ticks`, `ohlcv`, `orderbook_snapshots`, `orderbook_deltas`,
`derivatives_metrics`, `onchain_metrics`, `features`, `model_predictions`,
`regime_predictions`, `signals`, `risk_decisions`, `backtests`, `simulation_runs`,
`research_runs`, `model_registry`, `paper_orders`, `fills`, `positions`,
`portfolio_snapshots`, `audit_events`.

Phase 0 (`data/migrations/0001_init.sql`) created `signals`, `risk_decisions`, and
`audit_events` — the tables that directly correspond to the contracts implemented
before there was any ingestion pipeline (Section 6, Section 7, and a minimal audit
trail). Phase 1 (`data/migrations/0002_market_data.sql`) added `market_ticks`, `ohlcv`,
and `orderbook_snapshots`, written by `services/market-data`'s Binance adapter
(Section 3.1, 3.2, 3.4). `orderbook_deltas` and the remaining tables in this list are
still deferred to whichever phase first reads or writes them — Phase 1 ingests
top-of-book snapshots only (see `services/market-data/README.md`), not incremental
diffs, so `orderbook_deltas` has no producer yet.

## 10. Source of truth

`packages/contracts/src/*.ts` (zod schemas) is authoritative for anything defined in
this document. `packages/contracts` ships unit tests asserting valid examples pass and
invalid examples (wrong enum, missing required field, wrong type) fail.
