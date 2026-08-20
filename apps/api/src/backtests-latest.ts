import type { QueryablePool } from "./db.js";

interface BacktestDbRow {
  strategy_id: string;
  symbol: string;
  interval: string;
  dataset_version: string;
  metrics: Record<string, number | null>;
  created_at: string;
}

export interface BacktestSummary {
  strategyId: string;
  symbol: string;
  interval: string;
  datasetVersion: string;
  metrics: Record<string, number | null>;
  createdAt: string;
}

/**
 * Reads the latest backtest row per (strategy_id, symbol) from `backtests`
 * (data/migrations/0004_backtests.sql), written by
 * `python -m backtester.research_runner`. Same per-symbol query shape as
 * `getLatestDerivatives`/`getLatestSignals` in this directory. `metrics` is
 * whatever that runner actually computed — a key present with a `null`
 * value means the statistic was mathematically undefined at the sample
 * size it ran with (e.g. a Sharpe ratio needs return variance; a payoff
 * ratio needs both a winning and a losing trade), never a fabricated zero.
 * A (strategy, symbol) pair the runner hasn't scored yet is simply absent
 * from the response.
 */
export async function getLatestBacktests(
  pool: QueryablePool,
  symbols: readonly string[],
): Promise<BacktestSummary[]> {
  const results: BacktestSummary[] = [];
  for (const symbol of symbols) {
    const result = await pool.query<BacktestDbRow>(
      `SELECT DISTINCT ON (strategy_id)
              strategy_id, symbol, interval, dataset_version, metrics, created_at
       FROM backtests
       WHERE symbol = $1
       ORDER BY strategy_id, created_at DESC`,
      [symbol],
    );
    for (const row of result.rows) {
      results.push({
        strategyId: row.strategy_id,
        symbol: row.symbol,
        interval: row.interval,
        datasetVersion: row.dataset_version,
        metrics: row.metrics,
        createdAt: row.created_at,
      });
    }
  }
  return results;
}
