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
      if (sql.includes("FROM signals")) {
        return {
          rows: [
            {
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
            },
          ],
        };
      }
      if (sql.includes("FROM risk_decisions")) {
        return {
          rows: [
            {
              decision: "APPROVE",
              strategy_id: "trend_following_sma_v1",
              symbol: "BTC-USDT",
              reasons: [{ code: "OK", detail: "within limits" }],
              sizing_adjustment: null,
              timestamp: "2026-08-19T00:00:00Z",
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

describe("GET /signals/latest", () => {
  it("returns the latest signal + risk decision per symbol for an authenticated, entitled caller", async () => {
    const app = buildApp({ signals: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/signals/latest?symbols=BTC-USDT",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.signals).toHaveLength(1);
    expect(body.signals[0].candidate.strategyId).toBe("trend_following_sma_v1");
    expect(body.signals[0].riskDecision.decision).toBe("APPROVE");

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ signals: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/signals/latest" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("is not registered when signals deps are omitted", async () => {
    const app = buildApp({ auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/signals/latest",
      headers: sessionCookieHeader,
    });
    expect(response.statusCode).toBe(404);
    await app.close();
  });

  it("is not registered when auth deps are omitted, even with signals deps present", async () => {
    const app = buildApp({ signals: { pool: fakePool() } });
    const response = await app.inject({ method: "GET", url: "/signals/latest" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});
