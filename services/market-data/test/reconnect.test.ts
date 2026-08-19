import { describe, expect, it } from "vitest";
import { computeBackoffDelayMs } from "../src/reconnect.js";

describe("computeBackoffDelayMs", () => {
  const options = { baseDelayMs: 1000, maxDelayMs: 30_000 };

  it("returns the base delay on the first attempt", () => {
    expect(computeBackoffDelayMs(0, options)).toBe(1000);
  });

  it("doubles with each attempt", () => {
    expect(computeBackoffDelayMs(1, options)).toBe(2000);
    expect(computeBackoffDelayMs(2, options)).toBe(4000);
    expect(computeBackoffDelayMs(3, options)).toBe(8000);
  });

  it("caps at maxDelayMs", () => {
    expect(computeBackoffDelayMs(10, options)).toBe(30_000);
  });

  it("rejects a negative attempt", () => {
    expect(() => computeBackoffDelayMs(-1, options)).toThrow(RangeError);
  });
});
