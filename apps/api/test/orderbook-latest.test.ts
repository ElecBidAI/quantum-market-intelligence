import { describe, expect, it } from "vitest";
import { getLatestOrderBook } from "../src/orderbook-latest.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

describe("getLatestOrderBook", () => {
  it("shapes the latest snapshot into camelCase", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM orderbook_snapshots")) {
        return [
          {
            bids: [[100, 1]],
            asks: [[101, 1]],
            sequence_id: 42,
            timestamp: "2026-08-19T00:00:00Z",
          },
        ];
      }
      return [];
    });

    const book = await getLatestOrderBook(pool, "BTC-USDT");
    expect(book?.symbol).toBe("BTC-USDT");
    expect(book?.bids).toEqual([[100, 1]]);
    expect(book?.sequenceId).toBe(42);
  });

  it("returns null when nothing has been ingested yet", async () => {
    const pool = fakePool(() => []);
    expect(await getLatestOrderBook(pool, "ETH-USDT")).toBeNull();
  });

  it("only considers non-rejected rows", async () => {
    const pool = fakePool((sql) => {
      expect(sql).toMatch(/quality_status <> 'rejected'/);
      return [];
    });
    await getLatestOrderBook(pool, "BTC-USDT");
  });
});
