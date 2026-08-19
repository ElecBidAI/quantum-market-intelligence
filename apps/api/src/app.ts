import Fastify, { type FastifyInstance } from "fastify";
import { createLogger } from "@qmi/observability";

/**
 * Builds the Fastify app without starting it listening, so tests can use
 * `app.inject(...)` instead of binding a real port.
 *
 * Phase 0 only exposes a health check. Every future route that can influence
 * a trade must go through risk-engine (docs/risk/RISK-GOVERNANCE.md) — this
 * gateway does not implement any such route yet.
 */
export function buildApp(): FastifyInstance {
  const logger = createLogger({ service: "api" });
  const app = Fastify();

  app.addHook("onRequest", async (request) => {
    logger.info({ method: request.method, url: request.url }, "request received");
  });

  app.get("/health", async () => ({
    status: "ok",
    service: "qmi-api",
    time: new Date().toISOString(),
  }));

  return app;
}
