import { randomUUID } from "node:crypto";
import fastifyCookie from "@fastify/cookie";
import Fastify from "fastify";
import { describe, expect, it } from "vitest";
import type { QueryablePool } from "../src/db.js";
import { hashPassword } from "../src/password.js";
import { registerAuthRoutes, type AuthRouteDeps } from "../src/routes/auth.js";
import { sessionCookieOptions } from "../src/session.js";

interface FakeOrgRow {
  id: string;
  name: string;
}
interface FakeUserRow {
  id: string;
  organization_id: string;
  email: string;
  password_hash: string | null;
  role: "member" | "admin";
  created_at: string;
  plan: string;
}
interface FakeSessionRow {
  user_id: string;
  expires_at: string;
}
interface FakeAuditRow {
  event_type: string;
  actor: string;
  payload: unknown;
}

/**
 * A single in-memory fake standing in for organizations/users/sessions/
 * audit_events, keyed off substring-matching the SQL text — same idiom as
 * apps/api/test/market-routes.test.ts's fakePool().
 */
function fakeStore() {
  const orgs = new Map<string, FakeOrgRow>();
  const users = new Map<string, FakeUserRow>();
  const sessionsByHash = new Map<string, FakeSessionRow>();
  const auditEvents: FakeAuditRow[] = [];

  const pool: QueryablePool = {
    query: async (sql, params = []) => {
      if (sql.includes("SELECT id FROM users WHERE lower(email)")) {
        const [email] = params as [string];
        const found = [...users.values()].find((u) => u.email.toLowerCase() === email.toLowerCase());
        return { rows: found ? [{ id: found.id }] : [] };
      }
      if (sql.includes("INSERT INTO organizations")) {
        const [name] = params as [string];
        const id = randomUUID();
        orgs.set(id, { id, name });
        return { rows: [{ id }] };
      }
      if (sql.includes("INSERT INTO users") && sql.includes("RETURNING")) {
        const [organizationId, email, passwordHash] = params as [string, string, string | null];
        const id = randomUUID();
        const row: FakeUserRow = {
          id,
          organization_id: organizationId,
          email,
          password_hash: passwordHash,
          role: "admin",
          created_at: new Date().toISOString(),
          plan: "free",
        };
        users.set(id, row);
        return { rows: [row] };
      }
      if (sql.includes("SELECT id, organization_id, email, password_hash, role, created_at")) {
        const [email] = params as [string];
        const found = [...users.values()].find((u) => u.email.toLowerCase() === email.toLowerCase());
        return { rows: found ? [found] : [] };
      }
      if (sql.includes("SELECT u.id, u.organization_id, u.email, u.password_hash, u.role, u.created_at, o.plan")) {
        const [userId] = params as [string];
        const found = users.get(userId);
        return { rows: found ? [found] : [] };
      }
      if (sql.includes("SELECT u.id, u.organization_id, u.role, o.plan")) {
        const [userId] = params as [string];
        const found = users.get(userId);
        return { rows: found ? [{ id: found.id, organization_id: found.organization_id, role: found.role, plan: found.plan }] : [] };
      }
      if (sql.includes("INSERT INTO audit_events")) {
        const [eventType, actor, payload] = params as [string, string, string];
        auditEvents.push({ event_type: eventType, actor, payload: JSON.parse(payload) });
        return { rows: [] };
      }
      if (sql.includes("INSERT INTO sessions")) {
        const [userId, tokenHash, expiresAt] = params as [string, string, string];
        sessionsByHash.set(tokenHash, { user_id: userId, expires_at: expiresAt });
        return { rows: [] };
      }
      if (sql.includes("SELECT user_id, expires_at FROM sessions")) {
        const [tokenHash] = params as [string];
        const found = sessionsByHash.get(tokenHash);
        return { rows: found ? [found] : [] };
      }
      if (sql.includes("DELETE FROM sessions")) {
        const [tokenHash] = params as [string];
        sessionsByHash.delete(tokenHash);
        return { rows: [] };
      }
      throw new Error(`fakeStore: unhandled query: ${sql}`);
    },
  };

  return { pool, orgs, users, sessionsByHash, auditEvents };
}

function buildTestApp(pool: QueryablePool) {
  const app = Fastify();
  app.register(fastifyCookie);
  const deps: AuthRouteDeps = {
    pool,
    cookieName: "qmi_session",
    ttlSeconds: 3600,
    cookieOptions: sessionCookieOptions({ NODE_ENV: "test", SESSION_COOKIE_NAME: "qmi_session", SESSION_TTL_SECONDS: 3600 }),
  };
  registerAuthRoutes(app, deps);
  return app;
}

function extractSessionCookie(res: { cookies: { name: string; value: string }[] }): string {
  const cookie = res.cookies.find((c) => c.name === "qmi_session");
  if (!cookie) throw new Error("no session cookie set in response");
  return cookie.value;
}

describe("POST /auth/register", () => {
  it("creates an organization + admin user and starts a session", async () => {
    const { pool, auditEvents } = fakeStore();
    const app = buildTestApp(pool);

    const res = await app.inject({
      method: "POST",
      url: "/auth/register",
      payload: { email: "founder@acme.test", password: "correct-horse-battery", organizationName: "Acme" },
    });

    expect(res.statusCode).toBe(201);
    const body = res.json();
    expect(body.user.email).toBe("founder@acme.test");
    expect(body.user.role).toBe("admin");
    expect(body.user).not.toHaveProperty("passwordHash");
    expect(extractSessionCookie(res)).toBeTruthy();
    expect(auditEvents.some((e) => e.event_type === "register")).toBe(true);
  });

  it("rejects a duplicate email with 409", async () => {
    const { pool } = fakeStore();
    const app = buildTestApp(pool);
    const payload = { email: "dup@acme.test", password: "correct-horse-battery", organizationName: "Acme" };

    await app.inject({ method: "POST", url: "/auth/register", payload });
    const second = await app.inject({ method: "POST", url: "/auth/register", payload });

    expect(second.statusCode).toBe(409);
  });

  it("rejects an invalid body with 400", async () => {
    const { pool } = fakeStore();
    const app = buildTestApp(pool);
    const res = await app.inject({
      method: "POST",
      url: "/auth/register",
      payload: { email: "not-an-email", password: "x", organizationName: "" },
    });
    expect(res.statusCode).toBe(400);
  });
});

describe("POST /auth/login", () => {
  async function registeredStore(email: string, password: string) {
    const store = fakeStore();
    const app = buildTestApp(store.pool);
    await app.inject({
      method: "POST",
      url: "/auth/register",
      payload: { email, password, organizationName: "Acme" },
    });
    return { store, app };
  }

  it("logs in with correct credentials", async () => {
    const { app } = await registeredStore("trader@acme.test", "correct-horse-battery");
    const res = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { email: "trader@acme.test", password: "correct-horse-battery" },
    });
    expect(res.statusCode).toBe(200);
    expect(extractSessionCookie(res)).toBeTruthy();
  });

  it("rejects a wrong password with 401", async () => {
    const { app, store } = await registeredStore("trader2@acme.test", "correct-horse-battery");
    const res = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { email: "trader2@acme.test", password: "totally-wrong" },
    });
    expect(res.statusCode).toBe(401);
    expect(store.auditEvents.some((e) => e.event_type === "login_failed")).toBe(true);
  });

  it("rejects an unknown email with the same status/shape as a wrong password", async () => {
    const { pool } = fakeStore();
    const app = buildTestApp(pool);
    const unknownRes = await app.inject({
      method: "POST",
      url: "/auth/login",
      payload: { email: "nobody@acme.test", password: "whatever123" },
    });
    expect(unknownRes.statusCode).toBe(401);
    expect(unknownRes.json()).toEqual({ error: "invalid_credentials" });
  });
});

describe("POST /auth/logout and GET /auth/me", () => {
  async function loggedInApp() {
    const store = fakeStore();
    const app = buildTestApp(store.pool);
    const registerRes = await app.inject({
      method: "POST",
      url: "/auth/register",
      payload: { email: "member@acme.test", password: "correct-horse-battery", organizationName: "Acme" },
    });
    return { app, store, token: extractSessionCookie(registerRes) };
  }

  it("/auth/me returns the caller's identity for a valid session", async () => {
    const { app, token } = await loggedInApp();
    const res = await app.inject({ method: "GET", url: "/auth/me", headers: { cookie: `qmi_session=${token}` } });
    expect(res.statusCode).toBe(200);
    expect(res.json().user.email).toBe("member@acme.test");
    expect(res.json().plan).toBe("free");
  });

  it("/auth/me 401s without a session", async () => {
    const { app } = await loggedInApp();
    const res = await app.inject({ method: "GET", url: "/auth/me" });
    expect(res.statusCode).toBe(401);
  });

  it("/auth/logout revokes the session so a subsequent /auth/me 401s", async () => {
    const { app, token, store } = await loggedInApp();

    const logoutRes = await app.inject({
      method: "POST",
      url: "/auth/logout",
      headers: { cookie: `qmi_session=${token}` },
    });
    expect(logoutRes.statusCode).toBe(204);
    expect(store.auditEvents.some((e) => e.event_type === "logout")).toBe(true);

    const meRes = await app.inject({ method: "GET", url: "/auth/me", headers: { cookie: `qmi_session=${token}` } });
    expect(meRes.statusCode).toBe(401);
  });
});

describe("password hashing sanity", () => {
  it("registered users authenticate against an argon2 hash, not plaintext", async () => {
    const hash = await hashPassword("correct-horse-battery");
    expect(hash).toMatch(/^\$argon2/);
  });
});
