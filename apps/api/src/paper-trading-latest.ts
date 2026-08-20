import type { QueryablePool } from "./db.js";

interface PortfolioSnapshotDbRow {
  equity: number;
  realized_pnl_total: number;
  unrealized_pnl_total: number;
  gross_exposure_pct: number;
  net_exposure_pct: number;
  positions: Record<string, { netSize: number; avgEntryPrice: number }>;
  timestamp: string;
}

interface PaperOrderWithFillDbRow {
  order_id: string;
  strategy_id: string;
  symbol: string;
  direction: string;
  size_pct: number;
  risk_decision_code: string;
  created_at: string;
  fill_price: number | null;
  fill_timestamp: string | null;
}

export interface PortfolioSnapshot {
  equity: number;
  realizedPnlTotal: number;
  unrealizedPnlTotal: number;
  grossExposurePct: number;
  netExposurePct: number;
  positions: Record<string, { netSize: number; avgEntryPrice: number }>;
  timestamp: string;
}

export interface PaperOrderWithFill {
  orderId: string;
  strategyId: string;
  symbol: string;
  direction: string;
  sizePct: number;
  riskDecisionCode: string;
  createdAt: string;
  fillPrice: number | null;
  fillTimestamp: string | null;
}

/**
 * Reads the single latest portfolio snapshot
 * (data/migrations/0006_paper_execution.sql, written by
 * services/ai-council/src/ai_council/run_pipeline.py via
 * paper_execution.persistence.insert_portfolio_snapshot). Not per-symbol —
 * its own `positions` JSONB already breaks down by symbol. `null` if the
 * pipeline has never run.
 */
export async function getLatestPortfolioSnapshot(pool: QueryablePool): Promise<PortfolioSnapshot | null> {
  const result = await pool.query<PortfolioSnapshotDbRow>(
    `SELECT equity, realized_pnl_total, unrealized_pnl_total, gross_exposure_pct,
            net_exposure_pct, positions, "timestamp"
     FROM portfolio_snapshots
     ORDER BY "timestamp" DESC
     LIMIT 1`,
  );
  const row = result.rows[0];
  if (!row) return null;
  return {
    equity: row.equity,
    realizedPnlTotal: row.realized_pnl_total,
    unrealizedPnlTotal: row.unrealized_pnl_total,
    grossExposurePct: row.gross_exposure_pct,
    netExposurePct: row.net_exposure_pct,
    positions: row.positions,
    timestamp: row.timestamp,
  };
}

/**
 * Reads the most recent paper orders, each joined to its fill (every order
 * gets exactly one immediate, full fill — see paper_execution.fills'
 * FillSimulator — so this LEFT JOIN never fans out). `fillPrice`/
 * `fillTimestamp` are null only if an order was somehow recorded without
 * its fill, which shouldn't happen given how run_pipeline.py writes both
 * together, but the read path doesn't assume it.
 */
export async function getRecentPaperOrders(pool: QueryablePool, limit: number): Promise<PaperOrderWithFill[]> {
  const result = await pool.query<PaperOrderWithFillDbRow>(
    `SELECT o.order_id, o.strategy_id, o.symbol, o.direction, o.size_pct,
            o.risk_decision_code, o.created_at, f.price AS fill_price, f."timestamp" AS fill_timestamp
     FROM paper_orders o
     LEFT JOIN fills f ON f.order_id = o.order_id
     ORDER BY o.created_at DESC
     LIMIT $1`,
    [limit],
  );
  return result.rows.map((row) => ({
    orderId: row.order_id,
    strategyId: row.strategy_id,
    symbol: row.symbol,
    direction: row.direction,
    sizePct: row.size_pct,
    riskDecisionCode: row.risk_decision_code,
    createdAt: row.created_at,
    fillPrice: row.fill_price,
    fillTimestamp: row.fill_timestamp,
  }));
}
