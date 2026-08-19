import { z } from "zod";

/**
 * Schema for environment variables shared across QMI apps/services. Each
 * app/service should only read the subset it needs; this schema documents
 * the union so `.env.example` and this file stay in sync.
 */
export const envSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
  LOG_LEVEL: z.enum(["fatal", "error", "warn", "info", "debug", "trace"]).default("info"),
  API_PORT: z.coerce.number().int().positive().default(4000),
  DATABASE_URL: z.string().min(1).optional(),
  REDIS_URL: z.string().min(1).optional(),

  // --- Auth (docs/architecture/ACCESS-AND-LICENSING.md) ---
  SESSION_COOKIE_NAME: z.string().min(1).default("qmi_session"),
  SESSION_TTL_SECONDS: z.coerce.number().int().positive().default(604_800), // 7 days
  // 32-byte key (base64), used for AES-256-GCM encryption of stored SSO
  // client secrets. If unset, apps/api does not register SSO routes at all
  // (email/password auth still works) — see ACCESS-AND-LICENSING.md.
  AUTH_ENCRYPTION_KEY: z.string().min(1).optional(),
  // Externally-reachable base URL of apps/api itself (no trailing slash),
  // used to build the OIDC redirect_uri registered with an identity
  // provider. Distinct from NEXT_PUBLIC_API_URL, which is apps/web's view
  // of the same service — kept separate since one is browser-facing and
  // this one only matters server-to-server (this process to the IdP).
  API_PUBLIC_URL: z.string().min(1).default("http://localhost:4000"),
});
export type Env = z.infer<typeof envSchema>;

/**
 * Parses and validates a raw environment object (defaults to process.env).
 * Throws a descriptive error listing every invalid/missing field instead of
 * failing lazily the first time an unset variable is read.
 */
export function loadEnv(raw: Record<string, string | undefined> = process.env): Env {
  const result = envSchema.safeParse(raw);
  if (!result.success) {
    const details = result.error.issues
      .map((issue) => `  - ${issue.path.join(".") || "(root)"}: ${issue.message}`)
      .join("\n");
    throw new Error(`Invalid environment configuration:\n${details}`);
  }
  return result.data;
}
