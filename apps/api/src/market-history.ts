import type { QueryablePool } from "./db.js";

interface OhlcvHistoryDbRow {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface OhlcvBar {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export const MAX_HISTORY_LIMIT = 500;

/**
 * Reads up to `limit` non-rejected closed bars for one symbol, oldest
 * first — charting libraries (apps/web's PriceChart) want ascending time
 * order, the opposite of market-latest.ts's "most recent one" query.
 * Never fabricates a bar: a symbol with no history yet just gets an empty
 * array.
 */
export async function getOhlcvHistory(
  pool: QueryablePool,
  symbol: string,
  interval: string,
  limit: number,
): Promise<OhlcvBar[]> {
  const boundedLimit = Math.min(Math.max(limit, 1), MAX_HISTORY_LIMIT);
  const result = await pool.query<OhlcvHistoryDbRow>(
    `SELECT "timestamp", open, high, low, close, volume
     FROM ohlcv
     WHERE symbol = $1 AND interval = $2 AND quality_status <> 'rejected'
     ORDER BY "timestamp" ASC
     LIMIT $3`,
    [symbol, interval, boundedLimit],
  );
  return result.rows.map((row) => ({
    time: row.timestamp,
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    volume: row.volume,
  }));
}
