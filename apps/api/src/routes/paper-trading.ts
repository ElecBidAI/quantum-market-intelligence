import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import { getLatestPortfolioSnapshot, getRecentPaperOrders } from "../paper-trading-latest.js";
import type { QueryablePool } from "../db.js";

export interface PaperTradingRouteDeps {
  pool: QueryablePool;
}

const RECENT_ORDERS_LIMIT = 10;

/**
 * Registers:
 *   GET /paper-trading/latest — the latest portfolio snapshot (equity,
 *     realized/unrealized PnL, exposure, per-symbol positions) plus the
 *     most recent paper orders/fills (`paper_orders`/`fills`/
 *     `portfolio_snapshots`, all written by
 *     `python -m ai_council.run_pipeline`). Simulated paper trading only —
 *     nothing in this repository can place a real order.
 *
 * Requires `preHandler` (an authenticated session with the
 * `paper-trading:read` entitlement — built by app.ts).
 */
export function registerPaperTradingRoutes(
  app: FastifyInstance,
  deps: PaperTradingRouteDeps,
  preHandler: preHandlerHookHandler[],
): void {
  app.get("/paper-trading/latest", { preHandler }, async () => {
    const snapshot = await getLatestPortfolioSnapshot(deps.pool);
    const recentOrders = await getRecentPaperOrders(deps.pool, RECENT_ORDERS_LIMIT);
    return { snapshot, recentOrders };
  });
}
