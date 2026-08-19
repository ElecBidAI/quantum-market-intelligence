import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";
import type { QueryablePool } from "../src/market-latest.js";
import type { PubSub } from "../src/market-stream.js";

function fakePool(): QueryablePool {
  return {
    query: async (sql) => {
      if (sql.includes("FROM market_ticks")) {
        return { rows: [{ symbol: "BTC-USDT", exchange: "binance", price: 65000, side: "buy", timestamp: "t" }] };
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

describe("GET /market/latest", () => {
  it("returns latest state for the default symbol universe", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() } });
    const response = await app.inject({ method: "GET", url: "/market/latest" });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.symbols).toHaveLength(2);
    expect(body.symbols.map((s: { symbol: string }) => s.symbol)).toEqual(["BTC-USDT", "ETH-USDT"]);
    expect(body.symbols[0].trade.price).toBe(65000);

    await app.close();
  });

  it("filters to a requested, known symbol", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() } });
    const response = await app.inject({ method: "GET", url: "/market/latest?symbols=ETH-USDT" });

    const body = response.json();
    expect(body.symbols).toHaveLength(1);
    expect(body.symbols[0].symbol).toBe("ETH-USDT");

    await app.close();
  });

  it("falls back to the default universe for an unknown requested symbol", async () => {
    const app = buildApp({ market: { pool: fakePool(), pubsub: fakePubSub() } });
    const response = await app.inject({ method: "GET", url: "/market/latest?symbols=DOGE-USDT" });

    const body = response.json();
    expect(body.symbols.map((s: { symbol: string }) => s.symbol)).toEqual(["BTC-USDT", "ETH-USDT"]);

    await app.close();
  });

  it("is not registered when market deps are omitted (Phase-0-only app)", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/market/latest" });
    expect(response.statusCode).toBe(404);
    await app.close();
  });
});
