import type { Basis, FundingRate, Ohlcv, OrderBookSnapshot, Trade } from "@qmi/contracts";
import type { Pool } from "pg";

/**
 * Raw INSERT helpers matching data/migrations/0002_market_data.sql exactly.
 * Every insert uses ON CONFLICT DO NOTHING on the natural key so a
 * reconnect that re-delivers a message already seen is idempotent instead
 * of erroring or duplicating a row.
 */

export async function insertTrade(pool: Pool, trade: Trade): Promise<void> {
  await pool.query(
    `INSERT INTO market_ticks
       (source, exchange, symbol, "timestamp", ingested_at, quality_status, schema_version,
        price, size, side, trade_id)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
     ON CONFLICT (exchange, symbol, trade_id, "timestamp") DO NOTHING`,
    [
      trade.source,
      trade.exchange,
      trade.symbol,
      trade.timestamp,
      trade.ingestedAt,
      trade.qualityStatus,
      trade.schemaVersion,
      trade.price,
      trade.size,
      trade.side,
      trade.tradeId,
    ],
  );
}

export async function insertOhlcv(pool: Pool, bar: Ohlcv): Promise<void> {
  await pool.query(
    `INSERT INTO ohlcv
       (source, exchange, symbol, "timestamp", ingested_at, quality_status, schema_version,
        interval, open, high, low, close, volume)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
     ON CONFLICT (exchange, symbol, interval, "timestamp") DO NOTHING`,
    [
      bar.source,
      bar.exchange,
      bar.symbol,
      bar.timestamp,
      bar.ingestedAt,
      bar.qualityStatus,
      bar.schemaVersion,
      bar.interval,
      bar.open,
      bar.high,
      bar.low,
      bar.close,
      bar.volume,
    ],
  );
}

export async function insertOrderBookSnapshot(pool: Pool, snapshot: OrderBookSnapshot): Promise<void> {
  await pool.query(
    `INSERT INTO orderbook_snapshots
       (source, exchange, symbol, "timestamp", ingested_at, quality_status, schema_version,
        bids, asks, sequence_id)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
     ON CONFLICT (exchange, symbol, sequence_id, "timestamp") DO NOTHING`,
    [
      snapshot.source,
      snapshot.exchange,
      snapshot.symbol,
      snapshot.timestamp,
      snapshot.ingestedAt,
      snapshot.qualityStatus,
      snapshot.schemaVersion,
      JSON.stringify(snapshot.bids),
      JSON.stringify(snapshot.asks),
      snapshot.sequenceId,
    ],
  );
}

export async function insertFundingRate(pool: Pool, fundingRate: FundingRate): Promise<void> {
  await pool.query(
    `INSERT INTO funding_rates
       (source, exchange, symbol, "timestamp", ingested_at, quality_status, schema_version,
        rate, interval_hours)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
     ON CONFLICT (exchange, symbol, "timestamp") DO NOTHING`,
    [
      fundingRate.source,
      fundingRate.exchange,
      fundingRate.symbol,
      fundingRate.timestamp,
      fundingRate.ingestedAt,
      fundingRate.qualityStatus,
      fundingRate.schemaVersion,
      fundingRate.rate,
      fundingRate.intervalHours,
    ],
  );
}

export async function insertBasis(pool: Pool, basis: Basis): Promise<void> {
  await pool.query(
    `INSERT INTO futures_basis
       (source, exchange, symbol, "timestamp", ingested_at, quality_status, schema_version,
        spot_price, futures_price, basis, annualized_basis)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
     ON CONFLICT (exchange, symbol, "timestamp") DO NOTHING`,
    [
      basis.source,
      basis.exchange,
      basis.symbol,
      basis.timestamp,
      basis.ingestedAt,
      basis.qualityStatus,
      basis.schemaVersion,
      basis.spotPrice,
      basis.futuresPrice,
      basis.basis,
      basis.annualizedBasis,
    ],
  );
}
