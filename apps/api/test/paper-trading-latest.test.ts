import { describe, expect, it } from "vitest";
import { getLatestPortfolioSnapshot, getRecentPaperOrders } from "../src/paper-trading-latest.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

describe("getLatestPortfolioSnapshot", () => {
  it("shapes the latest snapshot into camelCase", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM portfolio_snapshots")) {
        return [
          {
            equity: 100_000,
            realized_pnl_total: 12.5,
            unrealized_pnl_total: -3.2,
            gross_exposure_pct: 0.02,
            net_exposure_pct: 0.02,
            positions: { "BTC-USDT": { netSize: 0.02, avgEntryPrice: 65100 } },
            timestamp: "2026-08-19T00:00:00Z",
          },
        ];
      }
      return [];
    });

    const snapshot = await getLatestPortfolioSnapshot(pool);
    expect(snapshot?.equity).toBe(100_000);
    expect(snapshot?.realizedPnlTotal).toBe(12.5);
    expect(snapshot?.positions["BTC-USDT"]?.netSize).toBe(0.02);
  });

  it("returns null when the pipeline has never run", async () => {
    const pool = fakePool(() => []);
    expect(await getLatestPortfolioSnapshot(pool)).toBeNull();
  });
});

describe("getRecentPaperOrders", () => {
  it("shapes joined order+fill rows into camelCase", async () => {
    const pool = fakePool((sql, params) => {
      if (sql.includes("FROM paper_orders")) {
        expect(params).toEqual([5]);
        return [
          {
            order_id: "order-1",
            strategy_id: "trend_following_sma_v1",
            symbol: "BTC-USDT",
            direction: "LONG",
            size_pct: 0.02,
            risk_decision_code: "APPROVE",
            created_at: "2026-08-19T00:00:00Z",
            fill_price: 65100,
            fill_timestamp: "2026-08-19T00:00:00Z",
          },
        ];
      }
      return [];
    });

    const [order] = await getRecentPaperOrders(pool, 5);
    expect(order?.orderId).toBe("order-1");
    expect(order?.fillPrice).toBe(65100);
  });

  it("returns an empty list when nothing has been persisted yet", async () => {
    const pool = fakePool(() => []);
    expect(await getRecentPaperOrders(pool, 10)).toEqual([]);
  });
});
