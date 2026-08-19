import { describe, expect, it } from "vitest";
import { getLatestMarketState, type QueryablePool } from "../src/market-latest.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

describe("getLatestMarketState", () => {
  it("returns trade and bar for a symbol that has both", async () => {
    const pool = fakePool((sql, params) => {
      if (sql.includes("FROM market_ticks")) {
        return [{ symbol: params[0], exchange: "binance", price: 65000, side: "buy", timestamp: "t1" }];
      }
      if (sql.includes("FROM ohlcv")) {
        return [
          {
            symbol: params[0],
            exchange: "binance",
            interval: "1m",
            open: 1,
            high: 2,
            low: 0.5,
            close: 1.5,
            volume: 10,
            timestamp: "t2",
          },
        ];
      }
      return [];
    });

    const [state] = await getLatestMarketState(pool, ["BTC-USDT"]);
    expect(state?.symbol).toBe("BTC-USDT");
    expect(state?.trade?.price).toBe(65000);
    expect(state?.bar?.close).toBe(1.5);
  });

  it("returns null trade/bar for a symbol with no data yet (never fabricates a value)", async () => {
    const pool = fakePool(() => []);
    const [state] = await getLatestMarketState(pool, ["ETH-USDT"]);
    expect(state).toEqual({ symbol: "ETH-USDT", trade: null, bar: null });
  });

  it("queries each requested symbol independently", async () => {
    const queried: string[] = [];
    const pool = fakePool((_sql, params) => {
      queried.push(params[0] as string);
      return [];
    });
    await getLatestMarketState(pool, ["BTC-USDT", "ETH-USDT"]);
    expect(queried).toEqual(["BTC-USDT", "BTC-USDT", "ETH-USDT", "ETH-USDT"]);
  });

  it("only considers non-rejected rows", async () => {
    const pool = fakePool((sql) => {
      expect(sql).toMatch(/quality_status <> 'rejected'/);
      return [];
    });
    await getLatestMarketState(pool, ["BTC-USDT"]);
  });
});
