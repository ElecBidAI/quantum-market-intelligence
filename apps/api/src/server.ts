import { loadEnv } from "@qmi/config";
import { Pool } from "pg";
import { createClient } from "redis";
import { buildApp, type AppDeps } from "./app.js";
import { sessionCookieOptions } from "./session.js";
import { RedisPubSub } from "./market-stream.js";

const env = loadEnv();

async function main(): Promise<void> {
  // /auth/* (and, transitively, /market/*) are only registered when
  // DATABASE_URL is configured, so `pnpm dev` still boots (health check
  // only) without a local Postgres running. Sessions only need Postgres,
  // not Redis, so auth doesn't additionally require REDIS_URL.
  const deps: AppDeps = {};
  let pool: Pool | undefined;
  let subscriber: ReturnType<typeof createClient> | undefined;

  if (env.DATABASE_URL) {
    pool = new Pool({ connectionString: env.DATABASE_URL });
    const cookieOptions = sessionCookieOptions(env);

    deps.auth = {
      pool,
      cookieName: env.SESSION_COOKIE_NAME,
      ttlSeconds: env.SESSION_TTL_SECONDS,
      cookieOptions,
    };
    deps.council = { pool };
    deps.derivatives = { pool };
    deps.signals = { pool };
    deps.paperTrading = { pool };
    deps.research = { pool };

    if (env.AUTH_ENCRYPTION_KEY) {
      deps.sso = {
        pool,
        cookieName: env.SESSION_COOKIE_NAME,
        cookieOptions,
        ttlSeconds: env.SESSION_TTL_SECONDS,
        encryptionKey: env.AUTH_ENCRYPTION_KEY,
        apiBaseUrl: env.API_PUBLIC_URL,
      };
    }

    if (env.REDIS_URL) {
      subscriber = createClient({ url: env.REDIS_URL });
      subscriber.on("error", (error) => console.error("redis subscriber error:", error));
      await subscriber.connect();
      deps.market = { pool, pubsub: new RedisPubSub(subscriber) };
    }
  }

  const app = buildApp(deps);

  const address = await app.listen({ port: env.API_PORT, host: "0.0.0.0" });
  app.log.info(`qmi-api listening on ${address}`);

  const shutdown = async (): Promise<void> => {
    await app.close();
    await subscriber?.quit();
    await pool?.end();
    process.exit(0);
  };
  process.on("SIGINT", () => void shutdown());
  process.on("SIGTERM", () => void shutdown());
}

main().catch((error: unknown) => {
  console.error("qmi-api failed to start:", error);
  process.exit(1);
});
