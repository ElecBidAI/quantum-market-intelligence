import { describe, expect, it } from "vitest";
import { loadEnv } from "../src/index.js";

describe("loadEnv", () => {
  it("applies defaults when optional fields are absent", () => {
    const env = loadEnv({});
    expect(env.NODE_ENV).toBe("development");
    expect(env.LOG_LEVEL).toBe("info");
    expect(env.API_PORT).toBe(4000);
    expect(env.SESSION_COOKIE_NAME).toBe("qmi_session");
    expect(env.SESSION_TTL_SECONDS).toBe(604_800);
    expect(env.AUTH_ENCRYPTION_KEY).toBeUndefined();
  });

  it("coerces API_PORT from a string", () => {
    const env = loadEnv({ API_PORT: "5050" });
    expect(env.API_PORT).toBe(5050);
  });

  it("throws with a descriptive message on an invalid NODE_ENV", () => {
    expect(() => loadEnv({ NODE_ENV: "staging" })).toThrow(/NODE_ENV/);
  });

  it("throws with a descriptive message on a non-numeric API_PORT", () => {
    expect(() => loadEnv({ API_PORT: "not-a-number" })).toThrow(/API_PORT/);
  });
});
