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
