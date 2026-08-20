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
      if (sql.includes("FROM funding_rates")) {
        return { rows: [{ rate: 0.0001, interval_hours: 8, timestamp: "2026-08-19T00:00:00Z" }] };
      }
      if (sql.includes("FROM futures_basis")) {
        return {
          rows: [
            {
              spot_price: 65000,
              futures_price: 65200,
              basis: 200,
              annualized_basis: 0.003,
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

describe("GET /derivatives/latest", () => {
  it("returns the latest derivatives per symbol for an authenticated, entitled caller", async () => {
    const app = buildApp({ derivatives: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/derivatives/latest?symbols=BTC-USDT",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.derivatives).toHaveLength(1);
    expect(body.derivatives[0].symbol).toBe("BTC-USDT");
    expect(body.derivatives[0].fundingRate.rate).toBe(0.0001);

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ derivatives: { pool: fakePool() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/derivatives/latest" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("is not registered when derivatives deps are omitted", async () => {
    const app = buildApp({ auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/derivatives/latest",
      headers: sessionCookieHeader,
    });
    expect(response.statusCode).toBe(404);
    await app.close();
  });

  it("is not registered when auth deps are omitted, even with derivatives deps present", async () => {
    const app = buildApp({ derivatives: { pool: fakePool() } });
    const response = await app.inject({ method: "GET", url: "/derivatives/latest" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});
