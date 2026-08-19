import type { FastifyInstance } from "fastify";
import { getLatestMarketState, type QueryablePool } from "../market-latest.js";
import { buildSymbolChannels, type PubSub } from "../market-stream.js";

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

/**
 * Registers:
 *   GET /market/latest?symbols=BTC-USDT,ETH-USDT — last known trade/bar per
 *     symbol, used to paint the dashboard's initial state.
 *   GET /stream/market?symbols=BTC-USDT,ETH-USDT — Server-Sent Events feed
 *     relaying whatever services/market-data publishes to Redis. Never
 *     synthesizes data: if nothing has been published yet, the client just
 *     receives no events until something real arrives.
 */
export function registerMarketRoutes(app: FastifyInstance, deps: MarketRouteDeps): void {
  app.get("/market/latest", async (request) => {
    const symbols = parseSymbols((request.query as Record<string, unknown>).symbols);
    const state = await getLatestMarketState(deps.pool, symbols);
    return { symbols: state };
  });

  app.get("/stream/market", async (request, reply) => {
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
}
