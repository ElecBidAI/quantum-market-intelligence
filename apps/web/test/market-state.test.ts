import { describe, expect, it } from "vitest";
import {
  applyLatestSnapshot,
  applyOhlcvEvent,
  applyTickEvent,
  initMarketState,
  isLive,
} from "../lib/market-state.js";

describe("initMarketState", () => {
  it("starts every symbol with null fields (never fabricates a value)", () => {
    const state = initMarketState(["BTC-USDT", "ETH-USDT"]);
    expect(state["BTC-USDT"]).toEqual({
      symbol: "BTC-USDT",
      exchange: null,
      lastPrice: null,
      lastBar: null,
      lastUpdate: null,
    });
    expect(Object.keys(state)).toEqual(["BTC-USDT", "ETH-USDT"]);
  });
});

describe("applyLatestSnapshot", () => {
  it("fills in trade and bar data for a known symbol", () => {
    const state = initMarketState(["BTC-USDT"]);
    const next = applyLatestSnapshot(state, [
      {
        symbol: "BTC-USDT",
        trade: { exchange: "binance", price: 65000, timestamp: "2026-08-19T12:00:00.000Z" },
        bar: {
          exchange: "binance",
          interval: "1m",
          open: 1,
          high: 2,
          low: 0.5,
          close: 1.5,
          volume: 10,
          timestamp: "2026-08-19T11:59:00.000Z",
        },
      },
    ]);

    expect(next["BTC-USDT"]?.lastPrice).toBe(65000);
    expect(next["BTC-USDT"]?.lastBar?.close).toBe(1.5);
    expect(next["BTC-USDT"]?.exchange).toBe("binance");
    // the later of the two timestamps wins
    expect(next["BTC-USDT"]?.lastUpdate).toBe("2026-08-19T12:00:00.000Z");
  });

  it("leaves a symbol with no data yet at all-null", () => {
    const state = initMarketState(["ETH-USDT"]);
    const next = applyLatestSnapshot(state, [{ symbol: "ETH-USDT", trade: null, bar: null }]);
    expect(next["ETH-USDT"]).toEqual({
      symbol: "ETH-USDT",
      exchange: null,
      lastPrice: null,
      lastBar: null,
      lastUpdate: null,
    });
  });
});

describe("applyTickEvent", () => {
  it("updates price and lastUpdate for a tracked symbol", () => {
    const state = initMarketState(["BTC-USDT"]);
    const next = applyTickEvent(state, {
      symbol: "BTC-USDT",
      exchange: "binance",
      price: 65100,
      timestamp: "2026-08-19T12:00:01.000Z",
    });
    expect(next["BTC-USDT"]?.lastPrice).toBe(65100);
    expect(next["BTC-USDT"]?.lastUpdate).toBe("2026-08-19T12:00:01.000Z");
  });

  it("ignores an event for a symbol that isn't tracked", () => {
    const state = initMarketState(["BTC-USDT"]);
    const next = applyTickEvent(state, {
      symbol: "DOGE-USDT",
      exchange: "binance",
      price: 1,
      timestamp: "2026-08-19T12:00:01.000Z",
    });
    expect(next).toBe(state);
  });
});

describe("applyOhlcvEvent", () => {
  it("updates the last bar for a tracked symbol without touching lastPrice", () => {
    const state = applyTickEvent(initMarketState(["BTC-USDT"]), {
      symbol: "BTC-USDT",
      exchange: "binance",
      price: 65100,
      timestamp: "2026-08-19T12:00:01.000Z",
    });
    const next = applyOhlcvEvent(state, {
      symbol: "BTC-USDT",
      exchange: "binance",
      interval: "1m",
      open: 65000,
      high: 65200,
      low: 64900,
      close: 65100,
      volume: 12,
      timestamp: "2026-08-19T12:01:00.000Z",
    });
    expect(next["BTC-USDT"]?.lastBar?.close).toBe(65100);
    expect(next["BTC-USDT"]?.lastPrice).toBe(65100); // unchanged from the tick
  });
});

describe("isLive", () => {
  const now = new Date("2026-08-19T12:00:30.000Z");

  it("is false when there has never been an update", () => {
    expect(isLive(null, now)).toBe(false);
  });

  it("is true within the staleness threshold", () => {
    expect(isLive("2026-08-19T12:00:10.000Z", now)).toBe(true);
  });

  it("is false beyond the staleness threshold", () => {
    expect(isLive("2026-08-19T11:59:00.000Z", now)).toBe(false);
  });
});
