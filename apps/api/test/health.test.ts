import { describe, expect, it } from "vitest";
import { buildApp } from "../src/app.js";

describe("GET /health", () => {
  it("returns status ok", async () => {
    const app = buildApp();
    const response = await app.inject({ method: "GET", url: "/health" });

    expect(response.statusCode).toBe(200);
    const body = response.json();
    expect(body.status).toBe("ok");
    expect(body.service).toBe("qmi-api");
    expect(typeof body.time).toBe("string");

    await app.close();
  });
});
