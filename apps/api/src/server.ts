import { loadEnv } from "@qmi/config";
import { Pool } from "pg";
import { createClient } from "redis";
import { buildApp } from "./app.js";
import { RedisPubSub } from "./market-stream.js";

const env = loadEnv();

async function main(): Promise<void> {
  // /market/latest and /stream/market are only registered when DATABASE_URL
  // and REDIS_URL are configured, so `pnpm dev` still boots (health check
  // only) without a local Postgres/Redis running.
  let market: { pool: Pool; subscriber: ReturnType<typeof createClient> } | undefined;

  if (env.DATABASE_URL && env.REDIS_URL) {
    const pool = new Pool({ connectionString: env.DATABASE_URL });
    const subscriber = createClient({ url: env.REDIS_URL });
    subscriber.on("error", (error) => console.error("redis subscriber error:", error));
    await subscriber.connect();
    market = { pool, subscriber };
  }

  const app = buildApp(
    market
      ? { market: { pool: market.pool, pubsub: new RedisPubSub(market.subscriber) } }
      : {},
  );

  const address = await app.listen({ port: env.API_PORT, host: "0.0.0.0" });
  app.log.info(`qmi-api listening on ${address}`);

  const shutdown = async (): Promise<void> => {
    await app.close();
    await market?.subscriber.quit();
    await market?.pool.end();
    process.exit(0);
  };
  process.on("SIGINT", () => void shutdown());
  process.on("SIGTERM", () => void shutdown());
}

main().catch((error: unknown) => {
  console.error("qmi-api failed to start:", error);
  process.exit(1);
});
