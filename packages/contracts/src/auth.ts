import { z } from "zod";
import { isoTimestamp } from "./common.js";

/**
 * Access & licensing contracts (docs/architecture/ACCESS-AND-LICENSING.md).
 * These are separate from the market/strategy/risk/derivatives domain: they
 * describe who is allowed to call the platform and what plan they're on, not
 * anything about markets.
 *
 * `user` and `ssoConnection` are `.strict()` deliberately: a stray field
 * (e.g. a `passwordHash` or `clientSecret` accidentally spread onto a
 * response object) fails validation loudly instead of silently serializing
 * a secret to a client. Neither schema has a field for the corresponding
 * secret at all — that's the actual guarantee; `.strict()` just makes a
 * mistake in the calling code fail fast too.
 */

export const plan = z.enum(["free", "pro", "enterprise"]);
export type Plan = z.infer<typeof plan>;

export const role = z.enum(["member", "admin"]);
export type Role = z.infer<typeof role>;

export const organization = z
  .object({
    id: z.string().uuid(),
    name: z.string().min(1),
    plan,
    createdAt: isoTimestamp,
  })
  .strict();
export type Organization = z.infer<typeof organization>;

/** Public-safe user shape. Never carries password_hash. */
export const user = z
  .object({
    id: z.string().uuid(),
    organizationId: z.string().uuid(),
    email: z.string().email(),
    role,
    createdAt: isoTimestamp,
  })
  .strict();
export type User = z.infer<typeof user>;

/** Public-safe SSO connection shape. Never carries the client secret. */
export const ssoConnection = z
  .object({
    id: z.string().uuid(),
    organizationId: z.string().uuid(),
    issuer: z.string().url(),
    clientId: z.string().min(1),
    createdAt: isoTimestamp,
  })
  .strict();
export type SsoConnection = z.infer<typeof ssoConnection>;

/**
 * Gate-able capabilities. Adding the next feature is a matter of extending
 * this union and `ENTITLEMENTS` below, not building a new mechanism.
 */
export type Feature =
  | "market-data:read"
  | "council-narrative:read"
  | "strategy-signals:read"
  | "paper-trading:read";

/**
 * Plan -> feature map. All three plans currently grant every feature
 * (nothing to differentiate on yet); this map is still the single source
 * of truth `apps/api`'s `requireEntitlement` reads, so introducing a
 * plan-gated feature later is a one-line edit here, not a new code path.
 */
const ALL_FEATURES: Feature[] = [
  "market-data:read",
  "council-narrative:read",
  "strategy-signals:read",
  "paper-trading:read",
];

export const ENTITLEMENTS: Record<Plan, ReadonlySet<Feature>> = {
  free: new Set(ALL_FEATURES),
  pro: new Set(ALL_FEATURES),
  enterprise: new Set(ALL_FEATURES),
};
