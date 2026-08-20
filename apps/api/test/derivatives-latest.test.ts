import { describe, expect, it } from "vitest";
import { getLatestDerivatives } from "../src/derivatives-latest.js";
import type { QueryablePool } from "../src/db.js";

function fakePool(rowsBySql: (sql: string, params: unknown[]) => unknown[]): QueryablePool {
  return {
    query: async (sql, params = []) => ({ rows: rowsBySql(sql, params) as never[] }),
  };
}

describe("getLatestDerivatives", () => {
  it("shapes funding rate and basis rows into camelCase", async () => {
    const pool = fakePool((sql) => {
      if (sql.includes("FROM funding_rates")) {
        return [{ rate: 0.0001, interval_hours: 8, timestamp: "2026-08-19T00:00:00Z" }];
      }
      if (sql.includes("FROM futures_basis")) {
        return [
          {
            spot_price: 65000,
            futures_price: 65200,
            basis: 200,
            annualized_basis: 0.003,
            timestamp: "2026-08-19T00:00:00Z",
          },
        ];
      }
      return [];
    });

    const [derivatives] = await getLatestDerivatives(pool, ["BTC-USDT"]);
    expect(derivatives?.symbol).toBe("BTC-USDT");
    expect(derivatives?.fundingRate?.rate).toBe(0.0001);
    expect(derivatives?.fundingRate?.intervalHours).toBe(8);
    expect(derivatives?.basis?.spotPrice).toBe(65000);
    expect(derivatives?.basis?.annualizedBasis).toBe(0.003);
  });

  it("returns null fields for a symbol with no derivatives data yet", async () => {
    const pool = fakePool(() => []);
    const [derivatives] = await getLatestDerivatives(pool, ["ETH-USDT"]);
    expect(derivatives).toEqual({ symbol: "ETH-USDT", fundingRate: null, basis: null });
  });

  it("queries each requested symbol independently", async () => {
    const queried: string[] = [];
    const pool = fakePool((_sql, params) => {
      queried.push(params[0] as string);
      return [];
    });
    await getLatestDerivatives(pool, ["BTC-USDT", "ETH-USDT"]);
    expect(queried).toEqual(["BTC-USDT", "BTC-USDT", "ETH-USDT", "ETH-USDT"]);
  });
});
