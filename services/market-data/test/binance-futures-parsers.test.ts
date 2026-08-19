import { describe, expect, it } from "vitest";
import {
  FUNDING_INTERVAL_HOURS,
  parseBasisMessage,
  parseFundingRateMessage,
} from "../src/adapters/binance-futures-parsers.js";

const FIXED_NOW = () => new Date("2026-08-19T12:00:00.000Z");

// Real Binance markPrice payload shape:
// https://binance-docs.github.io/apidocs/futures/en/#mark-price-stream
const validMarkPrice = {
  e: "markPriceUpdate",
  E: 1755604800000,
  s: "BTCUSDT",
  p: "65200.50",
  i: "65000.00",
  P: "65180.00",
  r: "0.00010000",
  T: 1755633600000,
};

describe("parseFundingRateMessage", () => {
  it("parses a valid markPrice payload into a funding rate", () => {
    const fundingRate = parseFundingRateMessage(validMarkPrice, FIXED_NOW);
    expect(fundingRate.symbol).toBe("BTC-USDT");
    expect(fundingRate.exchange).toBe("binance");
    expect(fundingRate.rate).toBeCloseTo(0.0001);
    expect(fundingRate.intervalHours).toBe(FUNDING_INTERVAL_HOURS);
    expect(fundingRate.timestamp).toBe(new Date(1755604800000).toISOString());
    expect(fundingRate.qualityStatus).toBe("ok");
  });

  it("handles a negative funding rate (shorts pay longs)", () => {
    const fundingRate = parseFundingRateMessage({ ...validMarkPrice, r: "-0.00020000" }, FIXED_NOW);
    expect(fundingRate.rate).toBeCloseTo(-0.0002);
  });

  it("rejects an unknown symbol", () => {
    expect(() => parseFundingRateMessage({ ...validMarkPrice, s: "DOGEUSDT" }, FIXED_NOW)).toThrow(
      /unknown symbol/,
    );
  });

  it("rejects a payload missing the funding rate field", () => {
    const { r: _r, ...withoutRate } = validMarkPrice;
    expect(() => parseFundingRateMessage(withoutRate, FIXED_NOW)).toThrow(/malformed/);
  });

  it("rejects a non-object payload", () => {
    expect(() => parseFundingRateMessage("not an object", FIXED_NOW)).toThrow(/not an object/);
  });
});

describe("parseBasisMessage", () => {
  it("parses a valid markPrice payload into a basis record", () => {
    const basis = parseBasisMessage(validMarkPrice, FIXED_NOW);
    expect(basis.symbol).toBe("BTC-USDT");
    expect(basis.spotPrice).toBeCloseTo(65000.0);
    expect(basis.futuresPrice).toBeCloseTo(65200.5);
    expect(basis.basis).toBeCloseTo(200.5);
    expect(basis.annualizedBasis).toBeCloseTo(200.5 / 65000.0);
  });

  it("handles backwardation (futures below index) as a negative basis", () => {
    const basis = parseBasisMessage({ ...validMarkPrice, p: "64800.00", i: "65000.00" }, FIXED_NOW);
    expect(basis.basis).toBeCloseTo(-200);
    expect(basis.annualizedBasis).toBeLessThan(0);
  });

  it("rejects a payload missing the index price field", () => {
    const { i: _i, ...withoutIndex } = validMarkPrice;
    expect(() => parseBasisMessage(withoutIndex, FIXED_NOW)).toThrow(/malformed/);
  });
});
