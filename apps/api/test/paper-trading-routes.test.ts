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
      if (sql.includes("FROM portfolio_snapshots")) {
        return {
          rows: [
            {
              equity: 100_000,
              realized_pnl_total: 0,
              unrealized_pnl_total: 0,
              gross_exposure_pct: 0.02,
              net_exposure_pct: 0.02,
              positions: { "BTC-USDT": { netSize: 0.02, avgEntryPrice: 65100 } },
              timestamp: "2026-08-19T00:00:00Z",
            },
          ],
        };
      }
      if (sql.includes("FROM paper_orders")) {
        return {
          rows: [
            {
              order_id: "order-1",
              strategy_id: "trend_following_sma_v1",
              symbol: "BTC-USDT",
              direction: "LONG",
              size_pct: 0.02,
              risk_decision_code: "APPROVE",
              created_at: "2026-08-19T00:00:00Z",
              fill_price: 65100,
              fill_timestamp: "2026-08-19T00:00:00Z",
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

describe("GET /paper-trading/latest", () => {
  it("returns the snapshot + recent orders for an authenticated, entitled caller", async () => {
    const app = buildApp({ paperTrading: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/paper-trading/latest",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.snapshot.equity).toBe(100_000);
    expect(body.recentOrders).toHaveLength(1);
    expect(body.recentOrders[0].orderId).toBe("order-1");

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ paperTrading: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/paper-trading/latest" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("is not registered when paperTrading deps are omitted", async () => {
    const app = buildApp({ auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/paper-trading/latest",
      headers: sessionCookieHeader,
    });
    expect(response.statusCode).toBe(404);
    await app.close();
  });

  it("is not registered when auth deps are omitted, even with paperTrading deps present", async () => {
    const app = buildApp({ paperTrading: { pool: fakePool() } });
    const response = await app.inject({ method: "GET", url: "/paper-trading/latest" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});
