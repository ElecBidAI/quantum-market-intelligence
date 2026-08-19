import type { QueryablePool } from "./db.js";

export type { QueryablePool } from "./db.js";

interface LatestTradeRow {
  symbol: string;
  exchange: string;
  price: number;
  side: string;
  timestamp: string;
}

interface LatestBarRow {
  symbol: string;
  exchange: string;
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

export interface LatestMarketState {
  symbol: string;
  trade: LatestTradeRow | null;
  bar: LatestBarRow | null;
}

/**
 * Reads the most recent non-rejected trade and OHLCV bar per symbol. Used to
 * seed the dashboard's initial state before the live SSE stream (see
 * market-stream.ts) starts delivering updates — see brief Section 18:
 * "UI must clearly show feed source and last-update timestamp."
 */
export async function getLatestMarketState(
  pool: QueryablePool,
  symbols: readonly string[],
): Promise<LatestMarketState[]> {
  const results: LatestMarketState[] = [];
  for (const symbol of symbols) {
    const tradeResult = await pool.query<LatestTradeRow>(
      `SELECT symbol, exchange, price, side, "timestamp"
       FROM market_ticks
       WHERE symbol = $1 AND quality_status <> 'rejected'
       ORDER BY "timestamp" DESC
       LIMIT 1`,
      [symbol],
    );
    const barResult = await pool.query<LatestBarRow>(
      `SELECT symbol, exchange, interval, open, high, low, close, volume, "timestamp"
       FROM ohlcv
       WHERE symbol = $1 AND quality_status <> 'rejected'
       ORDER BY "timestamp" DESC
       LIMIT 1`,
      [symbol],
    );
    results.push({
      symbol,
      trade: tradeResult.rows[0] ?? null,
      bar: barResult.rows[0] ?? null,
    });
  }
  return results;
}
