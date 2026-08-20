import { describe, expect, it } from "vitest";
import { getLatestCouncilNarratives } from "../src/council-latest.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

describe("getLatestCouncilNarratives", () => {
  it("shapes a row into camelCase, untouched narrative text", async () => {
    const pool = fakePool((sql, params) => {
      if (sql.includes("FROM council_narratives")) {
        return [
          {
            symbol: params[0],
            strategy_id: "trend_following_sma_v1",
            regime: "BULLISH_TREND",
            regime_confidence: 0.9,
            decision: "APPROVE",
            sizing_adjustment: null,
            final_stance: "SUPPORT",
            weighted_score: 1.0,
            narrative_en: "some broker narrative text",
            narrative_es: "algún texto narrativo del bróker",
            timestamp: "2026-08-19T00:00:00Z",
          },
        ];
      }
      return [];
    });

    const [narrative] = await getLatestCouncilNarratives(pool, ["BTC-USDT"]);
    expect(narrative?.symbol).toBe("BTC-USDT");
    expect(narrative?.strategyId).toBe("trend_following_sma_v1");
    expect(narrative?.narrativeEn).toBe("some broker narrative text");
    expect(narrative?.narrativeEs).toBe("algún texto narrativo del bróker");
    expect(narrative?.decision).toBe("APPROVE");
  });

  it("omits a symbol with no narrative yet, rather than fabricating one", async () => {
    const pool = fakePool(() => []);
    const narratives = await getLatestCouncilNarratives(pool, ["ETH-USDT"]);
    expect(narratives).toEqual([]);
  });

  it("queries each requested symbol independently", async () => {
    const queried: string[] = [];
    const pool = fakePool((_sql, params) => {
      queried.push(params[0] as string);
      return [];
    });
    await getLatestCouncilNarratives(pool, ["BTC-USDT", "ETH-USDT"]);
    expect(queried).toEqual(["BTC-USDT", "ETH-USDT"]);
  });
});
