import type { QueryablePool } from "./db.js";

interface OrderBookDbRow {
  bids: [number, number][];
  asks: [number, number][];
  sequence_id: number;
  timestamp: string;
}

export interface OrderBookSnapshot {
  symbol: string;
  bids: [number, number][];
  asks: [number, number][];
  sequenceId: number;
  timestamp: string;
}

/**
 * Reads the latest top-of-book snapshot for one symbol
 * (`orderbook_snapshots`, data/migrations/0002_market_data.sql, ingested
 * by services/market-data's `@depth20@100ms` Binance stream). `null` if
 * nothing has been ingested yet for this symbol — never a fabricated book.
 */
export async function getLatestOrderBook(pool: QueryablePool, symbol: string): Promise<OrderBookSnapshot | null> {
  const result = await pool.query<OrderBookDbRow>(
    `SELECT bids, asks, sequence_id, "timestamp"
     FROM orderbook_snapshots
     WHERE symbol = $1 AND quality_status <> 'rejected'
     ORDER BY "timestamp" DESC
     LIMIT 1`,
    [symbol],
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    symbol,
    bids: row.bids,
    asks: row.asks,
    sequenceId: row.sequence_id,
    timestamp: row.timestamp,
  };
}
