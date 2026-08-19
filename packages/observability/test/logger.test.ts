import { describe, expect, it } from "vitest";
import { createLogger } from "../src/index.js";

describe("createLogger", () => {
  it("binds the service name", () => {
    const logger = createLogger({ service: "test-service" });
    expect(logger.bindings().service).toBe("test-service");
  });

  it("defaults to info level", () => {
    const logger = createLogger({ service: "svc" });
    expect(logger.level).toBe("info");
  });

  it("respects a custom level", () => {
    const logger = createLogger({ service: "svc", level: "debug" });
    expect(logger.level).toBe("debug");
  });
});
