import { randomBytes, createHash } from "node:crypto";
import type { QueryablePool } from "./db.js";

interface SessionRow {
  user_id: string;
  expires_at: string;
}

/**
 * Opaque-token sessions: the raw token exists only here (returned once, at
 * creation) and in the client's cookie. Everywhere else — including this
 * table — only sees `hashToken(token)`. A database leak alone doesn't yield
 * a usable session, and revocation is a plain row delete (no JWT-revocation
 * problem to solve).
 */
export function generateOpaqueToken(): string {
  return randomBytes(32).toString("base64url");
}

export function hashToken(token: string): string {
  return createHash("sha256").update(token).digest("hex");
}

export async function createSession(
  pool: QueryablePool,
  userId: string,
  ttlSeconds: number,
): Promise<{ token: string; expiresAt: string }> {
  const token = generateOpaqueToken();
  const expiresAt = new Date(Date.now() + ttlSeconds * 1000).toISOString();
  await pool.query(
    `INSERT INTO sessions (user_id, token_hash, expires_at) VALUES ($1, $2, $3)`,
    [userId, hashToken(token), expiresAt],
  );
  return { token, expiresAt };
}

/** Returns null for a missing or expired session — that's an expected outcome, not an error. */
export async function validateSession(
  pool: QueryablePool,
  rawToken: string,
): Promise<{ userId: string } | null> {
  const result = await pool.query<SessionRow>(
    `SELECT user_id, expires_at FROM sessions WHERE token_hash = $1`,
    [hashToken(rawToken)],
  );
  const row = result.rows[0];
  if (!row) return null;
  if (new Date(row.expires_at).getTime() <= Date.now()) return null;
  return { userId: row.user_id };
}

export async function revokeSession(pool: QueryablePool, rawToken: string): Promise<void> {
  await pool.query(`DELETE FROM sessions WHERE token_hash = $1`, [hashToken(rawToken)]);
}

export interface CookieEnv {
  NODE_ENV: string;
  SESSION_COOKIE_NAME: string;
  SESSION_TTL_SECONDS: number;
}

/**
 * `sameSite: "lax"` is safe here because apps/web reaches apps/api through a
 * same-origin Next.js rewrite proxy (docs/architecture/ACCESS-AND-LICENSING.md),
 * not a cross-site request — no need for `SameSite=None` + mandatory HTTPS-in-dev.
 */
export function sessionCookieOptions(env: CookieEnv): {
  httpOnly: true;
  secure: boolean;
  sameSite: "lax";
  path: "/";
  maxAge: number;
} {
  return {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: env.SESSION_TTL_SECONDS,
  };
}
