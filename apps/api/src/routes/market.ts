import type { FastifyInstance, preHandlerHookHandler } from "fastify";
import { getOhlcvHistory } from "../market-history.js";
import { getLatestMarketState, type QueryablePool } from "../market-latest.js";
import { buildSymbolChannels, type PubSub } from "../market-stream.js";
import { getLatestOrderBook } from "../orderbook-latest.js";

/**
 * Phase 1 universe (docs/architecture/QMI-MASTER-ARCHITECTURE.md). Kept as
 * apps/api's own small constant rather than importing from
 * services/market-data — the two services only share state through
 * Postgres/Redis, not code, per the service-boundary rule in that doc.
 */
export const DEFAULT_SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

export interface MarketRouteDeps {
  pool: QueryablePool;
  pubsub: PubSub;
}

function parseSymbols(raw: unknown): string[] {
  if (typeof raw !== "string" || raw.trim().length === 0) return [...DEFAULT_SYMBOLS];
  const requested = raw
    .split(",")
    .map((s) => s.trim())
    .filter((s) => (DEFAULT_SYMBOLS as readonly string[]).includes(s));
  return requested.length > 0 ? requested : [...DEFAULT_SYMBOLS];
}

function parseSingleSymbol(raw: unknown): string {
  if (typeof raw === "string" && (DEFAULT_SYMBOLS as readonly string[]).includes(raw)) return raw;
  return DEFAULT_SYMBOLS[0];
}

const DEFAULT_HISTORY_LIMIT = 200;

function parseLimit(raw: unknown): number {
  const parsed = typeof raw === "string" ? Number.parseInt(raw, 10) : NaN;
  return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_HISTORY_LIMIT;
}

/**
 * Registers:
 *   GET /market/latest?symbols=BTC-USDT,ETH-USDT — last known trade/bar per
 *     symbol, used to paint the dashboard's initial state.
 *   GET /stream/market?symbols=BTC-USDT,ETH-USDT — Server-Sent Events feed
 *     relaying whatever services/market-data publishes to Redis. Never
 *     synthesizes data: if nothing has been published yet, the client just
 *     receives no events until something real arrives.
 *   GET /market/history?symbol=BTC-USDT&interval=1m&limit=200 — up to
 *     `limit` (capped at market-history.ts's MAX_HISTORY_LIMIT) closed
 *     bars for one symbol, oldest first — for apps/web's PriceChart to
 *     seed a candlestick series before live updates take over via
 *     /stream/market.
 *   GET /market/orderbook?symbol=BTC-USDT — the latest top-of-book
 *     snapshot (`orderbook_snapshots`, ingested by services/market-data's
 *     `@depth20@100ms` stream). `orderBook: null` if nothing's been
 *     ingested yet for that symbol.
 *
 * All four routes require `preHandler` (an authenticated session with the
 * `market-data:read` entitlement — see entitlements.ts's `protect()`,
 * built and passed in by app.ts). This module deliberately doesn't import
 * entitlements.ts itself, so a route module never has direct access to more
 * than the specific preHandler chain its caller decided to give it.
 */
export function registerMarketRoutes(
  app: FastifyInstance,
  deps: MarketRouteDeps,
  preHandler: preHandlerHookHandler[],
): void {
  app.get("/market/latest", { preHandler }, async (request) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const state = await getLatestMarketState(deps.pool, symbols);
    return { symbols: state };
  });

  app.get("/stream/market", { preHandler }, async (request, reply) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const channels = symbols.flatMap(buildSymbolChannels);

    reply.hijack();
    const res = reply.raw;
    res.writeHead(200, {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    });
    res.write(": connected\n\n");

    for (const { type, channel } of channels) {
      await deps.pubsub.subscribe(channel, (message) => {
        res.write(`event: ${type}\ndata: ${message}\n\n`);
      });
    }

    request.raw.on("close", () => {
      void Promise.all(channels.map((c) => deps.pubsub.unsubscribe(c.channel)));
    });
  });

  app.get("/market/history", { preHandler }, async (request) => {
    const query = request.query as Record<string, unknown>;
    const symbol = parseSingleSymbol(query.symbol);
    const interval = typeof query.interval === "string" && query.interval.length > 0 ? query.interval : "1m";
    const limit = parseLimit(query.limit);
    const bars = await getOhlcvHistory(deps.pool, symbol, interval, limit);
    return { symbol, interval, bars };
  });

  app.get("/market/orderbook", { preHandler }, async (request) => {
    const symbol = parseSingleSymbol((request.query as Record<string, unknown>).symbol);
    const orderBook = await getLatestOrderBook(deps.pool, symbol);
    return { orderBook };
  });
}
