import { createHash } from "node:crypto";
import fastifyCookie from "@fastify/cookie";
import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import type { Plan } from "@qmi/contracts";
import type { QueryablePool } from "../src/db.js";
import { authenticate, type EntitlementsDeps, protect, requireEntitlement } from "../src/entitlements.js";

const FAKE_TOKEN = "tok";
const FAKE_USER_ID = "user-1";

function fakeDeps(plan: Plan): EntitlementsDeps {
  const pool: QueryablePool = {
    query: async (sql, params) => {
      if (sql.includes("FROM sessions")) {
        const hash = (params as string[] | undefined)?.[0];
        if (hash === createHash("sha256").update(FAKE_TOKEN).digest("hex")) {
          return { rows: [{ user_id: FAKE_USER_ID, expires_at: new Date(Date.now() + 60_000).toISOString() }] };
        }
        return { rows: [] };
      }
      if (sql.includes("FROM users u")) {
        return { rows: [{ id: FAKE_USER_ID, organization_id: "org-1", role: "member", plan }] };
      }
      return { rows: [] };
    },
  };
  return { pool, cookieName: "qmi_session" };
}

function buildTestApp(deps: EntitlementsDeps) {
  const app = Fastify();
  app.register(fastifyCookie);
  app.get("/protected", { preHandler: authenticate(deps) }, async () => ({ ok: true }));
  app.get("/gated", { preHandler: protect(deps, "market-data:read") }, async () => ({ ok: true }));
  return app;
}

describe("authenticate", () => {
  it("401s with no cookie", async () => {
    const app = buildTestApp(fakeDeps("free"));
    const res = await app.inject({ method: "GET", url: "/protected" });
    expect(res.statusCode).toBe(401);
  });

  it("401s with an unrecognized token", async () => {
    const app = buildTestApp(fakeDeps("free"));
    const res = await app.inject({ method: "GET", url: "/protected", headers: { cookie: "qmi_session=bogus" } });
    expect(res.statusCode).toBe(401);
  });

  it("succeeds for a valid session", async () => {
    const app = buildTestApp(fakeDeps("free"));
    const res = await app.inject({
      method: "GET",
      url: "/protected",
      headers: { cookie: `qmi_session=${FAKE_TOKEN}` },
    });
    expect(res.statusCode).toBe(200);
  });
});

describe("protect (authenticate + requireEntitlement, real ENTITLEMENTS map)", () => {
  it("401s with no session at all", async () => {
    const app = buildTestApp(fakeDeps("free"));
    const res = await app.inject({ method: "GET", url: "/gated" });
    expect(res.statusCode).toBe(401);
  });

  it("200s for every plan, since all plans currently grant market-data:read", async () => {
    for (const plan of ["free", "pro", "enterprise"] as const) {
      const app = buildTestApp(fakeDeps(plan));
      const res = await app.inject({
        method: "GET",
        url: "/gated",
        headers: { cookie: `qmi_session=${FAKE_TOKEN}` },
      });
      expect(res.statusCode).toBe(200);
    }
  });
});

describe("requireEntitlement", () => {
  it("throws a programmer error when used without authenticate (request.user unset)", async () => {
    const handler = requireEntitlement("market-data:read");
    const fakeRequest = { user: undefined } as unknown as Parameters<typeof handler>[0];
    const fakeReply = { code: () => fakeReply, send: async () => fakeReply } as unknown as Parameters<
      typeof handler
    >[1];
    await expect(handler(fakeRequest, fakeReply, () => {})).rejects.toThrow(/authenticate/);
  });

  it("403s when the caller's plan lacks the feature under an injected entitlements map", async () => {
    const restrictiveMap = { free: new Set([]), pro: new Set(["market-data:read"] as const), enterprise: new Set(["market-data:read"] as const) };
    const handler = requireEntitlement("market-data:read", restrictiveMap);

    let statusCode: number | undefined;
    const fakeReply = {
      code(code: number) {
        statusCode = code;
        return fakeReply;
      },
      send: async () => fakeReply,
    } as unknown as Parameters<typeof handler>[1];
    const fakeRequest = {
      user: { id: "u1", organizationId: "o1", role: "member", plan: "free" },
    } as unknown as Parameters<typeof handler>[0];

    await handler(fakeRequest, fakeReply, () => {});
    expect(statusCode).toBe(403);
  });

  it("passes through (no reply sent) when the caller's plan has the feature under an injected map", async () => {
    const restrictiveMap = { free: new Set([]), pro: new Set(["market-data:read"] as const), enterprise: new Set(["market-data:read"] as const) };
    const handler = requireEntitlement("market-data:read", restrictiveMap);

    let codeCalled = false;
    const fakeReply = {
      code() {
        codeCalled = true;
        return fakeReply;
      },
      send: async () => fakeReply,
    } as unknown as Parameters<typeof handler>[1];
    const fakeRequest = {
      user: { id: "u1", organizationId: "o1", role: "member", plan: "pro" },
    } as unknown as Parameters<typeof handler>[0];

    await handler(fakeRequest, fakeReply, () => {});
    expect(codeCalled).toBe(false);
  });
});
