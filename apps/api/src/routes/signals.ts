import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import { getLatestSignals } from "../signals-latest.js";
import type { QueryablePool } from "../db.js";
import { DEFAULT_SYMBOLS } from "./market.js";

export interface SignalsRouteDeps {
  pool: QueryablePool;
}

function parseSymbols(raw: unknown): string[] {
  if (typeof raw !== "string" || raw.trim().length === 0) return [...DEFAULT_SYMBOLS];
  const requested = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => (DEFAULT_SYMBOLS as readonly string[]).includes(s));
  return requested.length > 0 ? requested : [...DEFAULT_SYMBOLS];
}

/**
 * Registers:
 *   GET /signals/latest?symbols=BTC-USDT,ETH-USDT — the latest strategy
 *     candidate + its risk decision per symbol (`signals`/`risk_decisions`,
 *     written by `python -m ai_council.run_pipeline`). Structured data —
 *     complements /council/narrative's prose, doesn't duplicate it.
 *
 * Requires `preHandler` (an authenticated session with the
 * `strategy-signals:read` entitlement — built by app.ts).
 */
export function registerSignalsRoutes(
  app: FastifyInstance,
  deps: SignalsRouteDeps,
  preHandler: preHandlerHookHandler[],
): void {
  app.get("/signals/latest", { preHandler }, async (request) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const signals = await getLatestSignals(deps.pool, symbols);
    return { signals };
  });
}
