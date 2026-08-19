import "@fastify/cookie";
import type { FastifyReply, FastifyRequest, preHandlerHookHandler } from "fastify";
import { ENTITLEMENTS, type Feature, type Plan, type Role } from "@qmi/contracts";
import type { QueryablePool } from "./db.js";
import { validateSession } from "./session.js";

declare module "fastify" {
  interface FastifyRequest {
    user?: {
      id: string;
      organizationId: string;
      role: Role;
      plan: Plan;
    };
  }
}

export interface EntitlementsDeps {
  pool: QueryablePool;
  cookieName: string;
}

interface UserWithPlanRow {
  id: string;
  organization_id: string;
  role: Role;
  plan: Plan;
}

/**
 * Reads the session cookie, validates it, and loads the caller's identity
 * (including their organization's plan) onto `request.user`. Replies 401
 * and short-circuits the route on any failure (missing/invalid/expired
 * session, or a session whose user no longer exists).
 */
export function authenticate(deps: EntitlementsDeps): preHandlerHookHandler {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    const token = request.cookies[deps.cookieName];
    if (!token) {
      await reply.code(401).send({ error: "unauthenticated" });
      return;
    }

    const session = await validateSession(deps.pool, token);
    if (!session) {
      await reply.code(401).send({ error: "unauthenticated" });
      return;
    }

    const result = await deps.pool.query<UserWithPlanRow>(
      `SELECT u.id, u.organization_id, u.role, o.plan
       FROM users u
       JOIN organizations o ON o.id = u.organization_id
       WHERE u.id = $1`,
      [session.userId],
    );
    const row = result.rows[0];
    if (!row) {
      await reply.code(401).send({ error: "unauthenticated" });
      return;
    }

    request.user = { id: row.id, organizationId: row.organization_id, role: row.role, plan: row.plan };
  };
}

/**
 * Gates a route on a plan entitlement. Must run after `authenticate` — if
 * `request.user` isn't set this throws a programmer error rather than
 * silently treating the request as unauthenticated, so misuse (wiring this
 * without `authenticate`) fails loudly in dev/tests instead of quietly
 * degrading into an always-401 or always-403 route.
 *
 * `entitlements` defaults to the real `ENTITLEMENTS` map and is only ever
 * overridden in tests (entitlements.test.ts) — every plan currently grants
 * the one feature that exists, so the 403 branch has no reachable case
 * against the real map yet; the injectable default is what makes that
 * branch testable without waiting for a plan-restricted feature to exist.
 */
export function requireEntitlement(
  feature: Feature,
  entitlements: Record<Plan, ReadonlySet<Feature>> = ENTITLEMENTS,
): preHandlerHookHandler {
  return async (request: FastifyRequest, reply: FastifyReply) => {
    if (!request.user) {
      throw new Error("requireEntitlement used without authenticate: request.user is not set");
    }
    if (!entitlements[request.user.plan].has(feature)) {
      await reply.code(403).send({ error: "entitlement_required", feature });
    }
  };
}

/**
 * The only blessed way to gate a route on a feature: bundles `authenticate`
 * + `requireEntitlement` so a route can never wire the entitlement check
 * without the identity check it depends on (mirrors this repo's other
 * structural-enforcement patterns, e.g. paper-execution's
 * `create_order_from_decision`). A route that only needs identity (no
 * specific feature — e.g. `/auth/me`) uses `authenticate` alone instead.
 */
export function protect(deps: EntitlementsDeps, feature: Feature): preHandlerHookHandler[] {
  return [authenticate(deps), requireEntitlement(feature)];
}
