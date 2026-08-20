import { describe, expect, it } from "vitest";
import { getLatestBacktests } from "../src/backtests-latest.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

const btcTrendRow = {
  strategy_id: "trend_following_sma_v1",
  symbol: "BTC-USDT",
  interval: "1m",
  dataset_version: "BTC-USDT:1m:2026-08-20T02:37:00Z..2026-08-20T03:56:00Z:80bars",
  metrics: { sampleSizeBars: 80, numTrades: 9, sharpeRatio: 216.88, payoffRatio: null },
  created_at: "2026-08-20T04:00:00Z",
};

const btcBreakoutRow = {
  ...btcTrendRow,
  strategy_id: "breakout_donchian_v1",
  metrics: { sampleSizeBars: 80, numTrades: 20, sharpeRatio: 216.94, payoffRatio: null },
};

describe("getLatestBacktests", () => {
  it("shapes every strategy's latest backtest for a symbol into camelCase", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM backtests")) return [btcBreakoutRow, btcTrendRow];
      return [];
    });

    const backtests = await getLatestBacktests(pool, ["BTC-USDT"]);
    expect(backtests).toHaveLength(2);
    expect(backtests[0]?.strategyId).toBe("breakout_donchian_v1");
    expect(backtests[0]?.datasetVersion).toBe(btcTrendRow.dataset_version);
    expect(backtests[0]?.metrics).toEqual(btcBreakoutRow.metrics);
  });

  it("preserves a null metric value rather than dropping or fabricating it", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM backtests")) return [btcTrendRow];
      return [];
    });

    const [backtest] = await getLatestBacktests(pool, ["BTC-USDT"]);
    expect(backtest?.metrics.payoffRatio).toBeNull();
  });

  it("omits a symbol with no backtest yet, rather than fabricating one", async () => {
    const pool = fakePool(() => []);
    const backtests = await getLatestBacktests(pool, ["ETH-USDT"]);
    expect(backtests).toEqual([]);
  });

  it("queries once per symbol, filtered to the latest row per strategy", async () => {
    const pool = fakePool((sql, params) => {
      if (sql.includes("FROM backtests")) {
        expect(sql).toContain("DISTINCT ON (strategy_id)");
        expect(params).toEqual(["BTC-USDT"]);
        return [btcTrendRow];
      }
      return [];
    });
    await getLatestBacktests(pool, ["BTC-USDT"]);
  });
});
