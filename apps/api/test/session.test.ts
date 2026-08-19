import { describe, expect, it } from "vitest";
import type { QueryablePool } from "../src/db.js";
import {
  createSession,
  generateOpaqueToken,
  hashToken,
  revokeSession,
  sessionCookieOptions,
  validateSession,
} from "../src/session.js";

/** In-memory fake of the `sessions` table, keyed by token_hash. */
function fakePool(): { pool: QueryablePool; rows: Map<string, { user_id: string; expires_at: string }> } {
  const rows = new Map<string, { user_id: string; expires_at: string }>();
  const pool: QueryablePool = {
    query: async (sql, params = []) => {
      if (sql.includes("INSERT INTO sessions")) {
        const [userId, tokenHash, expiresAt] = params as [string, string, string];
        rows.set(tokenHash, { user_id: userId, expires_at: expiresAt });
        return { rows: [] };
      }
      if (sql.includes("SELECT user_id, expires_at FROM sessions")) {
        const [tokenHash] = params as [string];
        const row = rows.get(tokenHash);
        return { rows: row ? [row] : [] };
      }
      if (sql.includes("DELETE FROM sessions")) {
        const [tokenHash] = params as [string];
        rows.delete(tokenHash);
        return { rows: [] };
      }
      return { rows: [] };
    },
  };
  return { pool, rows };
}

describe("generateOpaqueToken", () => {
  it("generates a different token on each call", () => {
    expect(generateOpaqueToken()).not.toBe(generateOpaqueToken());
  });
});

describe("hashToken", () => {
  it("never equals the raw token", () => {
    expect(hashToken("abc123")).not.toBe("abc123");
  });

  it("is deterministic", () => {
    expect(hashToken("abc123")).toBe(hashToken("abc123"));
  });
});

describe("createSession / validateSession / revokeSession", () => {
  it("validates a freshly created session", async () => {
    const { pool } = fakePool();
    const { token } = await createSession(pool, "user-1", 3600);
    expect(await validateSession(pool, token)).toEqual({ userId: "user-1" });
  });

  it("stores only the token hash, never the raw token", async () => {
    const { pool, rows } = fakePool();
    const { token } = await createSession(pool, "user-1", 3600);
    expect([...rows.keys()]).not.toContain(token);
    expect([...rows.keys()]).toContain(hashToken(token));
  });

  it("returns null for a token that was never issued", async () => {
    const { pool } = fakePool();
    expect(await validateSession(pool, "never-issued")).toBeNull();
  });

  it("returns null for an expired session", async () => {
    const { pool } = fakePool();
    const { token } = await createSession(pool, "user-1", -1);
    expect(await validateSession(pool, token)).toBeNull();
  });

  it("a revoked session no longer validates", async () => {
    const { pool } = fakePool();
    const { token } = await createSession(pool, "user-1", 3600);
    await revokeSession(pool, token);
    expect(await validateSession(pool, token)).toBeNull();
  });
});

describe("sessionCookieOptions", () => {
  const base = { SESSION_COOKIE_NAME: "qmi_session", SESSION_TTL_SECONDS: 100 };

  it("is always httpOnly with sameSite=lax", () => {
    const opts = sessionCookieOptions({ ...base, NODE_ENV: "development" });
    expect(opts.httpOnly).toBe(true);
    expect(opts.sameSite).toBe("lax");
  });

  it("is secure only in production", () => {
    expect(sessionCookieOptions({ ...base, NODE_ENV: "development" }).secure).toBe(false);
    expect(sessionCookieOptions({ ...base, NODE_ENV: "production" }).secure).toBe(true);
  });
});
