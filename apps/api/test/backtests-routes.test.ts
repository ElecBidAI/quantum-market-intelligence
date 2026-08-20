import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";
import type { EntitlementsDeps } from "../src/entitlements.js";
import type { QueryablePool } from "../src/db.js";

const FAKE_TOKEN = "test-session-token";
const FAKE_USER_ID = "11111111-1111-4111-8111-111111111111";

function fakePool(): QueryablePool {
  return {
    query: async (sql) => {
      if (sql.includes("FROM backtests")) {
        return {
          rows: [
            {
              strategy_id: "trend_following_sma_v1",
              symbol: "BTC-USDT",
              interval: "1m",
              dataset_version: "BTC-USDT:1m:2026-08-20T02:37:00Z..2026-08-20T03:56:00Z:80bars",
              metrics: { sampleSizeBars: 80, numTrades: 9, sharpeRatio: 216.88 },
              created_at: "2026-08-20T04:00:00Z",
            },
          ],
        };
      }
      return { rows: [] };
    },
  };
}

function fakeAuthPool(): QueryablePool {
  return {
    query: async (sql, params) => {
      if (sql.includes("FROM sessions")) {
        const tokenHash = params?.[0];
        if (tokenHash === createHash("sha256").update(FAKE_TOKEN).digest("hex")) {
          return { rows: [{ user_id: FAKE_USER_ID, expires_at: new Date(Date.now() + 60_000).toISOString() }] };
        }
        return { rows: [] };
      }
      if (sql.includes("FROM users u")) {
        return { rows: [{ id: FAKE_USER_ID, organization_id: "org-1", role: "member", plan: "pro" }] };
      }
      return { rows: [] };
    },
  };
}

function fakeAuthDeps(): EntitlementsDeps {
  return { pool: fakeAuthPool(), cookieName: "qmi_session" };
}

const sessionCookieHeader = { cookie: `qmi_session=${FAKE_TOKEN}` };

describe("GET /research/backtests", () => {
  it("returns the latest backtest per strategy/symbol for an authenticated, entitled caller", async () => {
    const app = buildApp({ research: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/research/backtests?symbols=BTC-USDT",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.backtests).toHaveLength(1);
    expect(body.backtests[0].strategyId).toBe("trend_following_sma_v1");
    expect(body.backtests[0].metrics.numTrades).toBe(9);

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ research: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/research/backtests" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("is not registered when research deps are omitted", async () => {
    const app = buildApp({ auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/research/backtests",
      headers: sessionCookieHeader,
    });
    expect(response.statusCode).toBe(404);
    await app.close();
  });

  it("is not registered when auth deps are omitted, even with research deps present", async () => {
    const app = buildApp({ research: { pool: fakePool() } });
    const response = await app.inject({ method: "GET", url: "/research/backtests" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});
