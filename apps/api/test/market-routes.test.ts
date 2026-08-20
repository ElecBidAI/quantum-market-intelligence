import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";
import type { EntitlementsDeps } from "../src/entitlements.js";
import type { QueryablePool } from "../src/market-latest.js";
import type { PubSub } from "../src/market-stream.js";

const FAKE_TOKEN = "test-session-token";
const FAKE_USER_ID = "11111111-1111-4111-8111-111111111111";

function fakePool(): QueryablePool {
  return {
    query: async (sql) => {
      if (sql.includes("FROM market_ticks")) {
        return { rows: [{ symbol: "BTC-USDT", exchange: "binance", price: 65000, side: "buy", timestamp: "t" }] };
      }
      if (sql.includes("FROM ohlcv")) {
        return {
          rows: [{ timestamp: "2026-08-19T00:00:00Z", open: 1, high: 2, low: 0.5, close: 1.5, volume: 10 }],
        };
      }
      if (sql.includes("FROM orderbook_snapshots")) {
        return {
          rows: [{ bids: [[100, 1]], asks: [[101, 1]], sequence_id: 1, timestamp: "2026-08-19T00:00:00Z" }],
        };
      }
      return { rows: [] };
    },
  };
}

function fakePubSub(): PubSub {
  return {
    subscribe: async () => {},
    unsubscribe: async () => {},
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

describe("GET /market/latest", () => {
  it("returns latest state for the default symbol universe", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/market/latest", headers: sessionCookieHeader });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.symbols).toHaveLength(2);
    expect(body.symbols.map((s: { symbol: string }) => s.symbol)).toEqual(["BTC-USDT", "ETH-USDT"]);
    expect(body.symbols[0].trade.price).toBe(65000);

    await app.close();
  });

  it("filters to a requested, known symbol", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/market/latest?symbols=ETH-USDT",
      headers: sessionCookieHeader,
    });

    const body = response.json();
    expect(body.symbols).toHaveLength(1);
    expect(body.symbols[0].symbol).toBe("ETH-USDT");

    await app.close();
  });

  it("falls back to the default universe for an unknown requested symbol", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/market/latest?symbols=DOGE-USDT",
      headers: sessionCookieHeader,
    });

    const body = response.json();
    expect(body.symbols.map((s: { symbol: string }) => s.symbol)).toEqual(["BTC-USDT", "ETH-USDT"]);

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/market/latest" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });

  it("is not registered when market deps are omitted (Phase-0-only app)", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/market/latest" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });

  it("is not registered when auth deps are omitted, even with market deps present", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() } });
    const response = await app.inject({ method: "GET", url: "/market/latest" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});

describe("GET /market/history", () => {
  it("returns ascending bars for a valid symbol", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/market/history?symbol=BTC-USDT&interval=1m&limit=200",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.symbol).toBe("BTC-USDT");
    expect(body.interval).toBe("1m");
    expect(body.bars).toHaveLength(1);
    expect(body.bars[0].close).toBe(1.5);

    await app.close();
  });

  it("falls back to the default symbol for an unknown one", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/market/history?symbol=DOGE-USDT",
      headers: sessionCookieHeader,
    });
    expect(response.json().symbol).toBe("BTC-USDT");
    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/market/history?symbol=BTC-USDT" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });
});

describe("GET /market/orderbook", () => {
  it("returns the latest snapshot for a valid symbol", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({
      method: "GET",
      url: "/market/orderbook?symbol=BTC-USDT",
      headers: sessionCookieHeader,
    });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.orderBook.symbol).toBe("BTC-USDT");
    expect(body.orderBook.bids).toEqual([[100, 1]]);

    await app.close();
  });

  it("rejects a request with no session cookie", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() }, auth: fakeAuthDeps() });
    const response = await app.inject({ method: "GET", url: "/market/orderbook?symbol=BTC-USDT" });
    expect(response.statusCode).toBe(401);
    await app.close();
  });
});
