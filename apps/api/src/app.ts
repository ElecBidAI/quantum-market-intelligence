import fastifyCookie from "@fastify/cookie";
import Fastify, { type FastifyInstance } from "fastify";
import { createLogger } from "@qmi/observability";
import { protect } from "./entitlements.js";
import { type AuthRouteDeps, registerAuthRoutes } from "./routes/auth.js";
import { type CouncilRouteDeps, registerCouncilRoutes } from "./routes/council.js";
import { type MarketRouteDeps, registerMarketRoutes } from "./routes/market.js";
import { type SsoRouteDeps, registerSsoRoutes } from "./routes/sso.js";

export interface AppDeps {
  /** Omitted in Phase 0-only contexts (e.g. the plain health-check test); required for /market/* and /stream/market. */
  market?: MarketRouteDeps;
  /** Required for /auth/* and, transitively, for /market/* and /council/* (all now require an authenticated session — see routes/market.ts, routes/council.ts). */
  auth?: AuthRouteDeps;
  /** Only present when AUTH_ENCRYPTION_KEY is configured — see server.ts. */
  sso?: SsoRouteDeps;
  /** Required for /council/narrative — see routes/council.ts. */
  council?: CouncilRouteDeps;
}

/**
 * Builds the Fastify app without starting it listening, so tests can use
 * `app.inject(...)` instead of binding a real port.
 *
 * Every route that can influence a trade must go through risk-engine
 * (docs/risk/RISK-GOVERNANCE.md) — this gateway implements no such route;
 * everything here is read-only market data plus account/session management.
 *
 * BREAKING (Access & Licensing): /market/latest and /stream/market now
 * require `deps.auth` in addition to `deps.market` — they're gated behind
 * `authenticate` + `requireEntitlement("market-data:read")`
 * (docs/architecture/ACCESS-AND-LICENSING.md). A caller that builds
 * `buildApp({ market })` without `auth` no longer gets those routes.
 */
export function buildApp(deps: AppDeps = {}): FastifyInstance {
  const logger = createLogger({ service: "api" });
  const app = Fastify();

  app.register(fastifyCookie);

  app.addHook("onRequest", async (request) => {
    logger.info({ method: request.method, url: request.url }, "request received");
  });

  app.get("/health", async () => ({
    status: "ok",
    service: "qmi-api",
    time: new Date().toISOString(),
  }));

  if (deps.auth) {
    registerAuthRoutes(app, deps.auth);
  }

  if (deps.sso) {
    registerSsoRoutes(app, deps.sso);
  }

  if (deps.market && deps.auth) {
    registerMarketRoutes(app, deps.market, protect(deps.auth, "market-data:read"));
  }

  if (deps.council && deps.auth) {
    registerCouncilRoutes(app, deps.council, protect(deps.auth, "council-narrative:read"));
  }

  return app;
}
