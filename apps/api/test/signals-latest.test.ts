import { describe, expect, it } from "vitest";
import { getLatestSignals } from "../src/signals-latest.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

const signalRow = {
  strategy_id: "trend_following_sma_v1",
  symbol: "BTC-USDT",
  venue: "binance",
  direction: "LONG",
  horizon: "4h",
  signal_strength: 0.8,
  entry_logic: { entryPrice: 100.0 },
  invalidation_logic: {},
  stop_logic: { stopPrice: 95.0 },
  target_logic: { targetPrice: 110.0 },
  expected_edge: 0.05,
  estimated_costs: 0.01,
  regime: "BULLISH_TREND",
  timestamp: "2026-08-19T00:00:00Z",
};

const riskDecisionRow = {
  decision: "APPROVE",
  strategy_id: "trend_following_sma_v1",
  symbol: "BTC-USDT",
  reasons: [{ code: "OK", detail: "within limits" }],
  sizing_adjustment: null,
  timestamp: "2026-08-19T00:00:00Z",
};

describe("getLatestSignals", () => {
  it("shapes a signal + its exactly-correlated risk decision into camelCase", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM signals")) return [signalRow];
      if (sql.includes("FROM risk_decisions")) return [riskDecisionRow];
      return [];
    });

    const [signal] = await getLatestSignals(pool, ["BTC-USDT"]);
    expect(signal?.symbol).toBe("BTC-USDT");
    expect(signal?.candidate.strategyId).toBe("trend_following_sma_v1");
    expect(signal?.candidate.entryLogic).toEqual({ entryPrice: 100.0 });
    expect(signal?.riskDecision?.decision).toBe("APPROVE");
  });

  it("returns riskDecision null when no exact strategy_id+timestamp match exists", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM signals")) return [signalRow];
      if (sql.includes("FROM risk_decisions")) return [];
      return [];
    });

    const [signal] = await getLatestSignals(pool, ["BTC-USDT"]);
    expect(signal?.riskDecision).toBeNull();
  });

  it("omits a symbol with no signal yet, rather than fabricating one", async () => {
    const pool = fakePool(() => []);
    const signals = await getLatestSignals(pool, ["ETH-USDT"]);
    expect(signals).toEqual([]);
  });

  it("correlates the risk decision by symbol, strategy_id, and exact timestamp", async () => {
    const pool = fakePool((sql, params) => {
      if (sql.includes("FROM signals")) return [signalRow];
      if (sql.includes("FROM risk_decisions")) {
        expect(params).toEqual(["BTC-USDT", signalRow.strategy_id, signalRow.timestamp]);
        return [riskDecisionRow];
      }
      return [];
    });
    await getLatestSignals(pool, ["BTC-USDT"]);
  });

  it("regression: two symbols sharing a strategy_id + timestamp each get their own risk decision, never the other's", async () => {
    // Both symbols picked the same strategy in the same run, with bars
    // sharing a last-bar timestamp — exactly the real scenario that
    // motivated adding risk_decisions.symbol (0011_risk_decisions_symbol.sql).
    const sharedTimestamp = "2026-08-19T00:00:00Z";
    const btcSignal = { ...signalRow, symbol: "BTC-USDT", timestamp: sharedTimestamp };
    const ethSignal = { ...signalRow, symbol: "ETH-USDT", timestamp: sharedTimestamp };
    const btcDecision = { ...riskDecisionRow, symbol: "BTC-USDT", decision: "APPROVE" };
    const ethDecision = { ...riskDecisionRow, symbol: "ETH-USDT", decision: "REJECT" };

    const pool = fakePool((sql, params) => {
      if (sql.includes("FROM signals")) {
        return params[0] === "BTC-USDT" ? [btcSignal] : [ethSignal];
      }
      if (sql.includes("FROM risk_decisions")) {
        return params[0] === "BTC-USDT" ? [btcDecision] : [ethDecision];
      }
      return [];
    });

    const signals = await getLatestSignals(pool, ["BTC-USDT", "ETH-USDT"]);
    const btc = signals.find((s) => s.symbol === "BTC-USDT");
    const eth = signals.find((s) => s.symbol === "ETH-USDT");
    expect(btc?.riskDecision?.decision).toBe("APPROVE");
    expect(eth?.riskDecision?.decision).toBe("REJECT");
  });
});
