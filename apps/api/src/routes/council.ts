import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import { getLatestCouncilNarratives } from "../council-latest.js";
import type { QueryablePool } from "../db.js";
import { DEFAULT_SYMBOLS } from "./market.js";

export interface CouncilRouteDeps {
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
 *   GET /council/narrative?symbols=BTC-USDT,ETH-USDT — the latest
 *     deterministic broker narrative per symbol
 *     (services/ai-council/src/ai_council/narrator.py, run by
 *     `python -m ai_council.run_narrative`). A symbol with no narrative
 *     yet is simply absent from the response.
 *
 * Requires `preHandler` (an authenticated session with the
 * `council-narrative:read` entitlement — built by app.ts, same pattern as
 * routes/market.ts).
 */
export function registerCouncilRoutes(
  app: FastifyInstance,
  deps: CouncilRouteDeps,
  preHandler: preHandlerHookHandler[],
): void {
  app.get("/council/narrative", { preHandler }, async (request) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const narratives = await getLatestCouncilNarratives(deps.pool, symbols);
    return { narratives };
  });
}
