import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import { getLatestDerivatives } from "../derivatives-latest.js";
import type { QueryablePool } from "../db.js";
import { DEFAULT_SYMBOLS } from "./market.js";

export interface DerivativesRouteDeps {
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
 *   GET /derivatives/latest?symbols=BTC-USDT,ETH-USDT — the latest funding
 *     rate and futures-vs-index basis per symbol
 *     (services/market-data's BinanceFuturesAdapter). A symbol with no
 *     derivatives data yet gets null fields, not a fabricated value.
 *
 * Requires `preHandler` (an authenticated session with the
 * `market-data:read` entitlement — derivatives are market data, same
 * category as spot trades/bars — built by app.ts, same pattern as
 * routes/market.ts/routes/council.ts).
 */
export function registerDerivativesRoutes(
  app: FastifyInstance,
  deps: DerivativesRouteDeps,
  preHandler: preHandlerHookHandler[],
): void {
  app.get("/derivatives/latest", { preHandler }, async (request) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const derivatives = await getLatestDerivatives(deps.pool, symbols);
    return { derivatives };
  });
}
