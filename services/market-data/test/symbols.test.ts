import { describe, expect, it } from "vitest";
import { toCanonicalSymbol } from "../src/symbols.js";

describe("toCanonicalSymbol", () => {
  it("resolves a lowercase Binance symbol", () => {
    expect(toCanonicalSymbol("btcusdt")).toBe("BTC-USDT");
    expect(toCanonicalSymbol("ethusdt")).toBe("ETH-USDT");
  });

  it("is case-insensitive", () => {
    expect(toCanonicalSymbol("BTCUSDT")).toBe("BTC-USDT");
  });

  it("returns undefined for an unknown symbol", () => {
    expect(toCanonicalSymbol("dogeusdt")).toBeUndefined();
  });
});
