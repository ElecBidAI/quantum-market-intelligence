import { describe, expect, it } from "vitest";
import type { Ohlcv, OrderBookSnapshot, Trade } from "@qmi/contracts";
import {
  BoundedIdSet,
  evaluateOhlcvQuality,
  evaluateOrderBookQuality,
  evaluateTradeQuality,
} from "../src/quality.js";

const NOW = new Date("2026-08-19T12:00:00.000Z");

function makeTrade(overrides: Partial<Trade> = {}): Trade {
  return {
    source: "binance-ws",
    exchange: "binance",
    symbol: "BTC-USDT",
    timestamp: NOW.toISOString(),
    ingestedAt: NOW.toISOString(),
    qualityStatus: "ok",
    schemaVersion: 1,
    price: 65000,
    size: 0.01,
    side: "buy",
    tradeId: "1",
    ...overrides,
  };
}

function makeSnapshot(overrides: Partial<OrderBookSnapshot> = {}): OrderBookSnapshot {
  return {
    source: "binance-ws",
    exchange: "binance",
    symbol: "BTC-USDT",
    timestamp: NOW.toISOString(),
    ingestedAt: NOW.toISOString(),
    qualityStatus: "ok",
    schemaVersion: 1,
    bids: [[100, 1]],
    asks: [[101, 1]],
    sequenceId: 1,
    ...overrides,
  };
}

function makeBar(overrides: Partial<Ohlcv> = {}): Ohlcv {
  return {
    source: "binance-ws",
    exchange: "binance",
    symbol: "BTC-USDT",
    timestamp: NOW.toISOString(),
    ingestedAt: NOW.toISOString(),
    qualityStatus: "ok",
    schemaVersion: 1,
    interval: "1m",
    open: 100,
    high: 110,
    low: 95,
    close: 105,
    volume: 10,
    ...overrides,
  };
}

describe("evaluateTradeQuality", () => {
  it("accepts a fresh, unseen trade", () => {
    const result = evaluateTradeQuality(makeTrade(), new Set(), NOW);
    expect(result).toEqual({ qualityStatus: "ok", reasons: [] });
  });

  it("rejects a duplicate trade id", () => {
    const result = evaluateTradeQuality(makeTrade({ tradeId: "1" }), new Set(["1"]), NOW);
    expect(result.qualityStatus).toBe("rejected");
    expect(result.reasons).toContain("DUPLICATE_TICK");
  });

  it("marks a stale trade as suspect", () => {
    const staleTimestamp = new Date(NOW.getTime() - 60_000).toISOString();
    const result = evaluateTradeQuality(makeTrade({ timestamp: staleTimestamp }), new Set(), NOW);
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("STALE_FEED");
  });

  it("marks a future timestamp beyond tolerance as suspect", () => {
    const futureTimestamp = new Date(NOW.getTime() + 60_000).toISOString();
    const result = evaluateTradeQuality(makeTrade({ timestamp: futureTimestamp }), new Set(), NOW);
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("ABNORMAL_TIMESTAMP_FUTURE");
  });
});

describe("evaluateOhlcvQuality", () => {
  it("accepts a fresh bar", () => {
    expect(evaluateOhlcvQuality(makeBar(), NOW)).toEqual({ qualityStatus: "ok", reasons: [] });
  });

  it("marks a stale bar as suspect", () => {
    const staleTimestamp = new Date(NOW.getTime() - 45_000).toISOString();
    const result = evaluateOhlcvQuality(makeBar({ timestamp: staleTimestamp }), NOW);
    expect(result.qualityStatus).toBe("suspect");
  });
});

describe("evaluateOrderBookQuality", () => {
  it("accepts a normal book", () => {
    expect(evaluateOrderBookQuality(makeSnapshot(), NOW)).toEqual({ qualityStatus: "ok", reasons: [] });
  });

  it("rejects a crossed book (best bid >= best ask)", () => {
    const result = evaluateOrderBookQuality(
      makeSnapshot({ bids: [[102, 1]], asks: [[101, 1]] }),
      NOW,
    );
    expect(result.qualityStatus).toBe("rejected");
    expect(result.reasons).toContain("CROSSED_BOOK");
  });

  it("rejects a book where best bid equals best ask", () => {
    const result = evaluateOrderBookQuality(
      makeSnapshot({ bids: [[100, 1]], asks: [[100, 1]] }),
      NOW,
    );
    expect(result.qualityStatus).toBe("rejected");
  });
});

describe("BoundedIdSet", () => {
  it("tracks recently added ids", () => {
    const set = new BoundedIdSet(2);
    set.add("a");
    expect(set.has("a")).toBe(true);
    expect(set.has("b")).toBe(false);
  });

  it("evicts the oldest id once capacity is exceeded", () => {
    const set = new BoundedIdSet(2);
    set.add("a");
    set.add("b");
    set.add("c");
    expect(set.has("a")).toBe(false);
    expect(set.has("b")).toBe(true);
    expect(set.has("c")).toBe(true);
  });
});
