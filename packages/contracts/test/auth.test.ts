import { describe, expect, it } from "vitest";
import { ENTITLEMENTS, organization, plan, ssoConnection, user } from "../src/index.js";

const baseTimestamps = {
  createdAt: "2026-08-19T00:00:00.000Z",
};

describe("organization", () => {
  it("accepts a valid organization", () => {
    const result = organization.safeParse({
      id: "5b1e6f2a-6b0e-4a3e-9c1a-1f2b3c4d5e6f",
      name: "Acme Capital",
      plan: "pro",
      ...baseTimestamps,
    });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid plan", () => {
    const result = organization.safeParse({
      id: "5b1e6f2a-6b0e-4a3e-9c1a-1f2b3c4d5e6f",
      name: "Acme Capital",
      plan: "ultra",
      ...baseTimestamps,
    });
    expect(result.success).toBe(false);
  });
});

describe("user", () => {
  const validUser = {
    id: "5b1e6f2a-6b0e-4a3e-9c1a-1f2b3c4d5e6f",
    organizationId: "6c2f7a3b-7c1f-4b4f-ad2b-2a3c4d5e6f7a",
    email: "trader@example.com",
    role: "member",
    ...baseTimestamps,
  };

  it("accepts a valid user", () => {
    expect(user.safeParse(validUser).success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = user.safeParse({ ...validUser, email: "not-an-email" });
    expect(result.success).toBe(false);
  });

  it("rejects an unknown field (e.g. an accidentally leaked passwordHash)", () => {
    const result = user.safeParse({ ...validUser, passwordHash: "should-never-be-here" });
    expect(result.success).toBe(false);
  });
});

describe("ssoConnection", () => {
  const validConnection = {
    id: "5b1e6f2a-6b0e-4a3e-9c1a-1f2b3c4d5e6f",
    organizationId: "6c2f7a3b-7c1f-4b4f-ad2b-2a3c4d5e6f7a",
    issuer: "https://idp.example.com",
    clientId: "abc123",
    ...baseTimestamps,
  };

  it("accepts a valid connection", () => {
    expect(ssoConnection.safeParse(validConnection).success).toBe(true);
  });

  it("rejects an unknown field (e.g. an accidentally leaked clientSecret)", () => {
    const result = ssoConnection.safeParse({ ...validConnection, clientSecret: "shh" });
    expect(result.success).toBe(false);
  });

  it("rejects a non-URL issuer", () => {
    const result = ssoConnection.safeParse({ ...validConnection, issuer: "not-a-url" });
    expect(result.success).toBe(false);
  });
});

describe("ENTITLEMENTS", () => {
  it.each(plan.options)("grants market-data:read to the %s plan", (planValue) => {
    expect(ENTITLEMENTS[planValue].has("market-data:read")).toBe(true);
  });
});
