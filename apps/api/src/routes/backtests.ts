import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import { getLatestBacktests } from "../backtests-latest.js";
import type { QueryablePool } from "../db.js";
import { DEFAULT_SYMBOLS } from "./market.js";

export interface BacktestsRouteDeps {
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
 *   GET /research/backtests?symbols=BTC-USDT,ETH-USDT — the latest real
 *     backtest result per (strategy, symbol), written by
 *     `python -m backtester.research_runner` against real ingested OHLCV
 *     history (`backtests`, data/migrations/0004_backtests.sql). Every
 *     strategy currently generating live candidates (services/strategy-
 *     engine) now has a real, auditable performance record here instead of
 *     only each strategy's own self-reported `expectedEdge`.
 *
 * Requires `preHandler` (an authenticated session with the
 * `research:read` entitlement — built by app.ts).
 */
export function registerBacktestsRoutes(
  app: FastifyInstance,
  deps: BacktestsRouteDeps,
  preHandler: preHandlerHookHandler[],
): void {
  app.get("/research/backtests", { preHandler }, async (request) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const backtests = await getLatestBacktests(deps.pool, symbols);
    return { backtests };
  });
}
