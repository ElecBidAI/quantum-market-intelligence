import { describe, expect, it } from "vitest";
import {
  ohlcv,
  orderBookDelta,
  orderBookSnapshot,
  quote,
  riskDecision,
  strategyCandidate,
  trade,
} from "../src/index.js";

const baseEnvelope = {
  source: "test-source",
  exchange: "binance",
  symbol: "BTC-USDT",
  timestamp: "2026-08-19T00:00:00.000Z",
  ingestedAt: "2026-08-19T00:00:00.100Z",
  qualityStatus: "ok" as const,
  schemaVersion: 1,
};

describe("trade", () => {
  it("accepts a valid trade", () => {
    const result = trade.safeParse({
      ...baseEnvelope,
      price: 65000.5,
      size: 0.01,
      side: "buy",
      tradeId: "abc123",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a negative price", () => {
    const result = trade.safeParse({
      ...baseEnvelope,
      price: -1,
      size: 0.01,
      side: "buy",
      tradeId: "abc123",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an invalid side", () => {
    const result = trade.safeParse({
      ...baseEnvelope,
      price: 1,
      size: 1,
      side: "sideways",
      tradeId: "abc123",
    });
    expect(result.success).toBe(false);
  });
});

describe("ohlcv", () => {
  const validBar = {
    ...baseEnvelope,
    interval: "1m",
    open: 100,
    high: 110,
    low: 95,
    close: 105,
    volume: 42,
  };

  it("accepts a valid bar", () => {
    expect(ohlcv.safeParse(validBar).success).toBe(true);
  });

  it("rejects high below low", () => {
    const result = ohlcv.safeParse({ ...validBar, high: 90, low: 95 });
    expect(result.success).toBe(false);
  });

  it("rejects high below open/close", () => {
    const result = ohlcv.safeParse({ ...validBar, high: 100, open: 101 });
    expect(result.success).toBe(false);
  });

  it("rejects missing schemaVersion", () => {
    const { schemaVersion: _schemaVersion, ...withoutVersion } = validBar;
    const result = ohlcv.safeParse(withoutVersion);
    expect(result.success).toBe(false);
  });
});

describe("quote", () => {
  it("accepts a valid quote", () => {
    const result = quote.safeParse({
      ...baseEnvelope,
      bidPrice: 100,
      bidSize: 1,
      askPrice: 100.5,
      askSize: 1,
    });
    expect(result.success).toBe(true);
  });
});

describe("orderBookSnapshot / orderBookDelta", () => {
  it("accepts a valid snapshot", () => {
    const result = orderBookSnapshot.safeParse({
      ...baseEnvelope,
      bids: [[100, 1], [99.5, 2]],
      asks: [[100.5, 1], [101, 3]],
      sequenceId: 42,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a snapshot with a malformed price level", () => {
    const result = orderBookSnapshot.safeParse({
      ...baseEnvelope,
      bids: [[100]],
      asks: [],
      sequenceId: 1,
    });
    expect(result.success).toBe(false);
  });

  it("accepts a valid delta", () => {
    const result = orderBookDelta.safeParse({
      ...baseEnvelope,
      side: "bid",
      price: 100,
      size: 0,
      sequenceId: 43,
      previousSequenceId: 42,
    });
    expect(result.success).toBe(true);
  });
});

describe("strategyCandidate", () => {
  it("accepts a valid candidate", () => {
    const result = strategyCandidate.safeParse({
      strategyId: "trend-follow-v1",
      symbol: "BTC-USDT",
      venue: "binance",
      direction: "LONG",
      horizon: "4h",
      signalStrength: 0.72,
      entryLogic: { rule: "close > sma200" },
      invalidationLogic: { rule: "close < sma200" },
      stopLogic: { atrMultiple: 2 },
      targetLogic: { atrMultiple: 4 },
      expectedEdge: 0.015,
      estimatedCosts: 0.002,
      regime: "bullish trend",
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid direction", () => {
    const result = strategyCandidate.safeParse({
      strategyId: "x",
      symbol: "BTC-USDT",
      venue: "binance",
      direction: "SIDEWAYS",
      horizon: "4h",
      signalStrength: 0,
      entryLogic: {},
      invalidationLogic: {},
      stopLogic: {},
      targetLogic: {},
      expectedEdge: 0,
      estimatedCosts: 0,
      regime: "sideways",
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(false);
  });
});

describe("riskDecision", () => {
  it("accepts APPROVE with no sizingAdjustment", () => {
    const result = riskDecision.safeParse({
      decision: "APPROVE",
      strategyId: "trend-follow-v1",
      reasons: [{ code: "OK", detail: "within all limits" }],
      sizingAdjustment: null,
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(true);
  });

  it("accepts REDUCE with a sizingAdjustment", () => {
    const result = riskDecision.safeParse({
      decision: "REDUCE",
      strategyId: "trend-follow-v1",
      reasons: [{ code: "LIQUIDITY_LIMIT", detail: "reduced for depth" }],
      sizingAdjustment: 0.5,
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(true);
  });

  it("rejects REDUCE without a sizingAdjustment", () => {
    const result = riskDecision.safeParse({
      decision: "REDUCE",
      strategyId: "trend-follow-v1",
      reasons: [],
      sizingAdjustment: null,
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(false);
  });

  it("rejects APPROVE that carries a sizingAdjustment", () => {
    const result = riskDecision.safeParse({
      decision: "APPROVE",
      strategyId: "trend-follow-v1",
      reasons: [],
      sizingAdjustment: 0.5,
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(false);
  });

  it("rejects an unknown decision value", () => {
    const result = riskDecision.safeParse({
      decision: "MAYBE",
      strategyId: "trend-follow-v1",
      reasons: [],
      sizingAdjustment: null,
      timestamp: "2026-08-19T00:00:00.000Z",
    });
    expect(result.success).toBe(false);
  });
});
