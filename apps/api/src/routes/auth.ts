import type { FastifyInstance, FastifyReply } from "fastify";
import { z } from "zod";
import { user as userSchema, type Plan } from "@qmi/contracts";
import { authenticate, type EntitlementsDeps } from "../entitlements.js";
import { hashPassword, verifyPassword } from "../password.js";
import { createSession, revokeSession, sessionCookieOptions } from "../session.js";

export interface AuthRouteDeps extends EntitlementsDeps {
  ttlSeconds: number;
  cookieOptions: ReturnType<typeof sessionCookieOptions>;
}

interface OrganizationRow {
  id: string;
}

interface UserRow {
  id: string;
  organization_id: string;
  email: string;
  password_hash: string | null;
  role: "member" | "admin";
  created_at: string;
}

interface UserWithPlanRow extends UserRow {
  plan: Plan;
}

const registerBody = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  organizationName: z.string().min(1),
});

const loginBody = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});

function toUserResponse(row: UserRow): z.infer<typeof userSchema> {
  return userSchema.parse({
    id: row.id,
    organizationId: row.organization_id,
    email: row.email,
    role: row.role,
    createdAt: new Date(row.created_at).toISOString(),
  });
}

async function writeAuditEvent(
  pool: EntitlementsDeps["pool"],
  eventType: string,
  actor: string,
  payload: Record<string, unknown>,
): Promise<void> {
  await pool.query(
    `INSERT INTO audit_events (event_type, actor, payload, "timestamp") VALUES ($1, $2, $3, now())`,
    [eventType, actor, JSON.stringify(payload)],
  );
}

async function setSessionCookie(
  reply: FastifyReply,
  deps: AuthRouteDeps,
  userId: string,
): Promise<void> {
  const { token } = await createSession(deps.pool, userId, deps.ttlSeconds);
  reply.setCookie(deps.cookieName, token, deps.cookieOptions);
}

/**
 * Business logic lives inline here rather than in a sibling flat file
 * (unlike market-latest.ts's single read query): each route is a distinct
 * multi-step sequence (hash/insert/audit/session), and the reusable
 * primitives it composes are already extracted into password.ts,
 * session.ts, and entitlements.ts.
 */
export function registerAuthRoutes(app: FastifyInstance, deps: AuthRouteDeps): void {
  app.post("/auth/register", async (request, reply) => {
    const parsed = registerBody.safeParse(request.body);
    if (!parsed.success) {
      return reply.code(400).send({ error: "invalid_request" });
    }
    const { email, password, organizationName } = parsed.data;

    const existing = await deps.pool.query<{ id: string }>(
      `SELECT id FROM users WHERE lower(email) = lower($1)`,
      [email],
    );
    if (existing.rows[0]) {
      return reply.code(409).send({ error: "email_already_registered" });
    }

    const orgResult = await deps.pool.query<OrganizationRow>(
      `INSERT INTO organizations (name) VALUES ($1) RETURNING id`,
      [organizationName],
    );
    const organizationId = orgResult.rows[0]!.id;

    const passwordHash = await hashPassword(password);
    const userResult = await deps.pool.query<UserRow>(
      `INSERT INTO users (organization_id, email, password_hash, role)
       VALUES ($1, $2, $3, 'admin')
       RETURNING id, organization_id, email, password_hash, role, created_at`,
      [organizationId, email, passwordHash],
    );
    const row = userResult.rows[0]!;

    await writeAuditEvent(deps.pool, "register", row.id, { organizationId });
    await setSessionCookie(reply, deps, row.id);

    return reply.code(201).send({ user: toUserResponse(row) });
  });

  app.post("/auth/login", async (request, reply) => {
    const parsed = loginBody.safeParse(request.body);
    if (!parsed.success) {
      return reply.code(400).send({ error: "invalid_request" });
    }
    const { email, password } = parsed.data;

    const result = await deps.pool.query<UserRow>(
      `SELECT id, organization_id, email, password_hash, role, created_at
       FROM users WHERE lower(email) = lower($1)`,
      [email],
    );
    const row = result.rows[0];

    // Identical failure response for "unknown email" and "wrong password" —
    // distinguishing them would let a caller enumerate registered emails.
    const valid = row?.password_hash ? await verifyPassword(row.password_hash, password) : false;
    if (!row || !valid) {
      await writeAuditEvent(deps.pool, "login_failed", email, {});
      return reply.code(401).send({ error: "invalid_credentials" });
    }

    await writeAuditEvent(deps.pool, "login", row.id, {});
    await setSessionCookie(reply, deps, row.id);

    return reply.send({ user: toUserResponse(row) });
  });

  app.post("/auth/logout", { preHandler: authenticate(deps) }, async (request, reply) => {
    const token = request.cookies[deps.cookieName];
    if (token) await revokeSession(deps.pool, token);
    reply.clearCookie(deps.cookieName, { path: deps.cookieOptions.path });
    await writeAuditEvent(deps.pool, "logout", request.user!.id, {});
    return reply.code(204).send();
  });

  app.get("/auth/me", { preHandler: authenticate(deps) }, async (request, reply) => {
    const result = await deps.pool.query<UserWithPlanRow>(
      `SELECT u.id, u.organization_id, u.email, u.password_hash, u.role, u.created_at, o.plan
       FROM users u JOIN organizations o ON o.id = u.organization_id
       WHERE u.id = $1`,
      [request.user!.id],
    );
    const row = result.rows[0];
    if (!row) return reply.code(401).send({ error: "unauthenticated" });

    return reply.send({ user: toUserResponse(row), plan: row.plan });
  });
}
