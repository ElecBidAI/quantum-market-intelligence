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
      if (sql.includes("FROM council_narratives")) {
        return {
          rows: [
            {
              symbol: "BTC-USDT",
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
          ],
        };
      }
      return { rows: [] };
    },
  };
}

/** Recognizes exactly FAKE_TOKEN as a valid session for a "pro"-plan user. */
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

describe("GET /council/narrative", () => {
  it("returns the latest narrative per symbol for an authenticated, entitled caller", async () => {
    const app = buildApp({ council: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/council/narrative?symbols=BTC-USDT",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.narratives).toHaveLength(1);
    expect(body.narratives[0].symbol).toBe("BTC-USDT");
    expect(body.narratives[0].narrativeEn).toBe("some broker narrative text");
    expect(body.narratives[0].narrativeEs).toBe("algún texto narrativo del bróker");

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ council: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/council/narrative" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("is not registered when council deps are omitted", async () => {
    const app = buildApp({ auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/council/narrative",
      headers: sessionCookieHeader,
    });
    expect(response.statusCode).toBe(404);
    await app.close();
  });

  it("is not registered when auth deps are omitted, even with council deps present", async () => {
    const app = buildApp({ council: { pool: fakePool() } });
    const response = await app.inject({ method: "GET", url: "/council/narrative" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});
