import { describe, expect, it } from "vitest";
import { getOhlcvHistory, MAX_HISTORY_LIMIT } from "../src/market-history.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

describe("getOhlcvHistory", () => {
  it("shapes rows into bars, oldest first", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM ohlcv")) {
        return [
          { timestamp: "2026-08-19T00:00:00Z", open: 1, high: 2, low: 0.5, close: 1.5, volume: 10 },
          { timestamp: "2026-08-19T00:01:00Z", open: 1.5, high: 2.5, low: 1, close: 2, volume: 12 },
        ];
      }
      return [];
    });

    const bars = await getOhlcvHistory(pool, "BTC-USDT", "1m", 200);
    expect(bars).toHaveLength(2);
    expect(bars[0]?.time).toBe("2026-08-19T00:00:00Z");
    expect(bars[0]?.close).toBe(1.5);
    expect(bars[1]?.time).toBe("2026-08-19T00:01:00Z");
  });

  it("queries ascending order and only non-rejected rows", async () => {
    const pool = fakePool((sql, params) => {
      expect(sql).toMatch(/ORDER BY "timestamp" ASC/);
      expect(sql).toMatch(/quality_status <> 'rejected'/);
      expect(params).toEqual(["BTC-USDT", "1m", 200]);
      return [];
    });
    await getOhlcvHistory(pool, "BTC-USDT", "1m", 200);
  });

  it("returns an empty array for a symbol with no history yet", async () => {
    const pool = fakePool(() => []);
    expect(await getOhlcvHistory(pool, "ETH-USDT", "1m", 200)).toEqual([]);
  });

  it("bounds the limit to MAX_HISTORY_LIMIT", async () => {
    const pool = fakePool((_sql, params) => {
      expect(params[2]).toBe(MAX_HISTORY_LIMIT);
      return [];
    });
    await getOhlcvHistory(pool, "BTC-USDT", "1m", 10_000);
  });

  it("bounds the limit to at least 1", async () => {
    const pool = fakePool((_sql, params) => {
      expect(params[2]).toBe(1);
      return [];
    });
    await getOhlcvHistory(pool, "BTC-USDT", "1m", -5);
  });
});
