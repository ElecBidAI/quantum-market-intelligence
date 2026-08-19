import { describe, expect, it } from "vitest";
import {
  parseDepthSnapshotMessage,
  parseKlineMessage,
  parseTradeMessage,
} from "../src/adapters/binance-parsers.js";

const FIXED_NOW = () => new Date("2026-08-19T12:00:00.000Z");

describe("parseTradeMessage", () => {
  const validTrade = {
    e: "trade",
    E: 1755604800000,
    s: "BTCUSDT",
    t: 12345,
    p: "65000.50",
    q: "0.01",
    T: 1755604799000,
    m: true,
    M: true,
  };

  it("parses a valid buyer-maker (sell-side) trade", () => {
    const trade = parseTradeMessage(validTrade, FIXED_NOW);
    expect(trade.symbol).toBe("BTC-USDT");
    expect(trade.exchange).toBe("binance");
    expect(trade.price).toBe(65000.5);
    expect(trade.size).toBe(0.01);
    expect(trade.side).toBe("sell");
    expect(trade.tradeId).toBe("12345");
    expect(trade.timestamp).toBe(new Date(1755604799000).toISOString());
    expect(trade.qualityStatus).toBe("ok");
  });

  it("maps m=false to a buy-side trade", () => {
    const trade = parseTradeMessage({ ...validTrade, m: false }, FIXED_NOW);
    expect(trade.side).toBe("buy");
  });

  it("rejects an unknown symbol", () => {
    expect(() => parseTradeMessage({ ...validTrade, s: "DOGEUSDT" }, FIXED_NOW)).toThrow(/unknown symbol/);
  });

  it("rejects a non-numeric price", () => {
    expect(() => parseTradeMessage({ ...validTrade, p: "not-a-number" }, FIXED_NOW)).toThrow(/not numeric/);
  });

  it("rejects a payload missing a required field", () => {
    const { m: _m, ...withoutSide } = validTrade;
    expect(() => parseTradeMessage(withoutSide, FIXED_NOW)).toThrow(/boolean field "m"/);
  });

  it("rejects a non-object payload", () => {
    expect(() => parseTradeMessage("not an object", FIXED_NOW)).toThrow(/not an object/);
  });
});

describe("parseKlineMessage", () => {
  const closedKline = {
    e: "kline",
    E: 1755604860000,
    s: "ETHUSDT",
    k: {
      t: 1755604800000,
      T: 1755604859999,
      s: "ETHUSDT",
      i: "1m",
      f: 100,
      L: 200,
      o: "3000.00",
      c: "3010.50",
      h: "3015.00",
      l: "2995.00",
      v: "120.5",
      n: 42,
      x: true,
      q: "362000",
      V: "60",
      Q: "180000",
      B: "0",
    },
  };

  it("parses a closed bar", () => {
    const bar = parseKlineMessage(closedKline, FIXED_NOW);
    expect(bar).not.toBeNull();
    expect(bar?.symbol).toBe("ETH-USDT");
    expect(bar?.interval).toBe("1m");
    expect(bar?.open).toBe(3000);
    expect(bar?.high).toBe(3015);
    expect(bar?.low).toBe(2995);
    expect(bar?.close).toBe(3010.5);
    expect(bar?.volume).toBe(120.5);
    expect(bar?.timestamp).toBe(new Date(1755604859999).toISOString());
  });

  it("returns null for an in-progress (unclosed) bar", () => {
    const openKline = { ...closedKline, k: { ...closedKline.k, x: false } };
    expect(parseKlineMessage(openKline, FIXED_NOW)).toBeNull();
  });

  it("rejects a payload missing the k object", () => {
    expect(() => parseKlineMessage({ e: "kline" }, FIXED_NOW)).toThrow(/object field "k"/);
  });
});

describe("parseDepthSnapshotMessage", () => {
  const validDepth = {
    lastUpdateId: 160,
    bids: [
      ["65000.00", "1.5"],
      ["64999.50", "2.0"],
    ],
    asks: [
      ["65000.50", "1.0"],
      ["65001.00", "3.0"],
    ],
  };

  it("parses a valid depth snapshot", () => {
    const snapshot = parseDepthSnapshotMessage(validDepth, "btcusdt", FIXED_NOW);
    expect(snapshot.symbol).toBe("BTC-USDT");
    expect(snapshot.sequenceId).toBe(160);
    expect(snapshot.bids).toEqual([
      [65000, 1.5],
      [64999.5, 2],
    ]);
    expect(snapshot.asks[0]).toEqual([65000.5, 1]);
  });

  it("rejects a malformed price level", () => {
    const malformed = { ...validDepth, bids: [["only-one-entry"]] };
    expect(() => parseDepthSnapshotMessage(malformed, "btcusdt", FIXED_NOW)).toThrow(/not a \[price, size\] pair/);
  });

  it("rejects an unknown symbol", () => {
    expect(() => parseDepthSnapshotMessage(validDepth, "dogeusdt", FIXED_NOW)).toThrow(/unknown symbol/);
  });
});
