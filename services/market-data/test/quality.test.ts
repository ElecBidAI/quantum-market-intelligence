import { describe, expect, it } from "vitest";
import type { Basis, FundingRate, Ohlcv, OrderBookSnapshot, Trade } from "@qmi/contracts";
import {
  BoundedIdSet,
  evaluateBasisQuality,
  evaluateFundingRateQuality,
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

function makeFundingRate(overrides: Partial<FundingRate> = {}): FundingRate {
  return {
    source: "binance-futures-ws",
    exchange: "binance",
    symbol: "BTC-USDT",
    timestamp: NOW.toISOString(),
    ingestedAt: NOW.toISOString(),
    qualityStatus: "ok",
    schemaVersion: 1,
    rate: 0.0001,
    intervalHours: 8,
    ...overrides,
  };
}

function makeBasis(overrides: Partial<Basis> = {}): Basis {
  return {
    source: "binance-futures-ws",
    exchange: "binance",
    symbol: "BTC-USDT",
    timestamp: NOW.toISOString(),
    ingestedAt: NOW.toISOString(),
    qualityStatus: "ok",
    schemaVersion: 1,
    spotPrice: 65000,
    futuresPrice: 65200,
    basis: 200,
    annualizedBasis: 200 / 65000,
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

describe("evaluateFundingRateQuality", () => {
  it("accepts a normal funding rate", () => {
    expect(evaluateFundingRateQuality(makeFundingRate(), NOW)).toEqual({
      qualityStatus: "ok",
      reasons: [],
    });
  });

  it("flags an extreme positive funding rate as suspect", () => {
    const result = evaluateFundingRateQuality(makeFundingRate({ rate: 0.01 }), NOW);
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("EXTREME_FUNDING_RATE");
  });

  it("flags an extreme negative funding rate as suspect", () => {
    const result = evaluateFundingRateQuality(makeFundingRate({ rate: -0.01 }), NOW);
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("EXTREME_FUNDING_RATE");
  });

  it("marks a stale funding rate as suspect", () => {
    const staleTimestamp = new Date(NOW.getTime() - 60_000).toISOString();
    const result = evaluateFundingRateQuality(makeFundingRate({ timestamp: staleTimestamp }), NOW);
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("STALE_FEED");
  });
});

describe("evaluateBasisQuality", () => {
  it("accepts a normal basis", () => {
    expect(evaluateBasisQuality(makeBasis(), NOW)).toEqual({ qualityStatus: "ok", reasons: [] });
  });

  it("flags an extreme basis as suspect", () => {
    const result = evaluateBasisQuality(
      makeBasis({ spotPrice: 65000, futuresPrice: 65000 * 1.1, basis: 65000 * 0.1 }),
      NOW,
    );
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("EXTREME_BASIS");
  });

  it("flags an extreme negative basis (backwardation) as suspect", () => {
    const result = evaluateBasisQuality(
      makeBasis({ spotPrice: 65000, futuresPrice: 65000 * 0.9, basis: -65000 * 0.1 }),
      NOW,
    );
    expect(result.qualityStatus).toBe("suspect");
    expect(result.reasons).toContain("EXTREME_BASIS");
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
