import Fastify, { type FastifyInstance } from "fastify";
import { createLogger } from "@qmi/observability";
import { type MarketRouteDeps, registerMarketRoutes } from "./routes/market.js";

export interface AppDeps {
  /** Omitted in Phase 0-only contexts (e.g. the plain health-check test); required for /market/* and /stream/market. */
  market?: MarketRouteDeps;
}

/**
 * Builds the Fastify app without starting it listening, so tests can use
 * `app.inject(...)` instead of binding a real port.
 *
 * Every route that can influence a trade must go through risk-engine
 * (docs/risk/RISK-GOVERNANCE.md) — this gateway implements no such route;
 * everything here is read-only market data.
 */
export function buildApp(deps: AppDeps = {}): FastifyInstance {
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

  if (deps.market) {
    registerMarketRoutes(app, deps.market);
  }

  return app;
}
