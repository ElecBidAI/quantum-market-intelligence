import { describe, expect, it } from "vitest";
import { basis, fundingRate, futuresCurvePoint, liquidationEvent, openInterest } from "../src/index.js";

const baseEnvelope = {
  source: "binance-futures-ws",
  exchange: "binance",
  symbol: "BTC-USDT",
  timestamp: "2026-08-19T00:00:00.000Z",
  ingestedAt: "2026-08-19T00:00:00.100Z",
  qualityStatus: "ok" as const,
  schemaVersion: 1,
};

describe("fundingRate", () => {
  it("accepts a valid funding rate", () => {
    const result = fundingRate.safeParse({ ...baseEnvelope, rate: 0.0001, intervalHours: 8 });
    expect(result.success).toBe(true);
  });

  it("accepts a negative rate (shorts pay longs)", () => {
    const result = fundingRate.safeParse({ ...baseEnvelope, rate: -0.0002, intervalHours: 8 });
    expect(result.success).toBe(true);
  });

  it("rejects a non-positive interval", () => {
    const result = fundingRate.safeParse({ ...baseEnvelope, rate: 0.0001, intervalHours: 0 });
    expect(result.success).toBe(false);
  });
});

describe("openInterest", () => {
  it("accepts valid open interest", () => {
    const result = openInterest.safeParse({ ...baseEnvelope, openInterest: 12345.6, notional: 800_000_000 });
    expect(result.success).toBe(true);
  });

  it("rejects negative open interest", () => {
    const result = openInterest.safeParse({ ...baseEnvelope, openInterest: -1, notional: 100 });
    expect(result.success).toBe(false);
  });
});

describe("basis", () => {
  it("accepts a valid basis record", () => {
    const result = basis.safeParse({
      ...baseEnvelope,
      spotPrice: 65000,
      futuresPrice: 65200,
      basis: 200,
      annualizedBasis: 0.045,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a non-positive spot price", () => {
    const result = basis.safeParse({
      ...baseEnvelope,
      spotPrice: 0,
      futuresPrice: 65200,
      basis: 200,
      annualizedBasis: 0.045,
    });
    expect(result.success).toBe(false);
  });
});

describe("liquidationEvent", () => {
  it("accepts a valid liquidation event", () => {
    const result = liquidationEvent.safeParse({
      ...baseEnvelope,
      side: "long",
      price: 64000,
      size: 1.5,
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid side", () => {
    const result = liquidationEvent.safeParse({ ...baseEnvelope, side: "flat", price: 100, size: 1 });
    expect(result.success).toBe(false);
  });
});

describe("futuresCurvePoint", () => {
  it("accepts a valid curve point", () => {
    const result = futuresCurvePoint.safeParse({
      ...baseEnvelope,
      expiry: "2026-12-26",
      price: 66000,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a non-positive price", () => {
    const result = futuresCurvePoint.safeParse({ ...baseEnvelope, expiry: "2026-12-26", price: -1 });
    expect(result.success).toBe(false);
  });
});
