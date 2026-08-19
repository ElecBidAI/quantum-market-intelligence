import { loadEnv } from "@qmi/config";
import { createLogger } from "@qmi/observability";
import { Pool } from "pg";
import { createClient } from "redis";
import { BinanceAdapter } from "./adapters/binance.js";
import { BinanceFuturesAdapter } from "./adapters/binance-futures.js";
import { insertBasis, insertFundingRate, insertOhlcv, insertOrderBookSnapshot, insertTrade } from "./persistence.js";
import { basisChannel, bookChannel, fundingRateChannel, ohlcvChannel, publishJson, tickChannel } from "./publish.js";
import {
  BoundedIdSet,
  evaluateBasisQuality,
  evaluateFundingRateQuality,
  evaluateOhlcvQuality,
  evaluateOrderBookQuality,
  evaluateTradeQuality,
} from "./quality.js";
import { PHASE1_SYMBOLS } from "./symbols.js";

const TRADE_ID_DEDUPE_WINDOW = 5_000;

async function main(): Promise<void> {
  const env = loadEnv();
  const logger = createLogger({ service: "market-data", level: env.LOG_LEVEL });

  if (!env.DATABASE_URL) throw new Error("DATABASE_URL is required for services/market-data");
  if (!env.REDIS_URL) throw new Error("REDIS_URL is required for services/market-data");

  const pool = new Pool({ connectionString: env.DATABASE_URL });
  const redis = createClient({ url: env.REDIS_URL });
  redis.on("error", (error) => logger.error({ error: String(error) }, "redis client error"));
  await redis.connect();

  const seenTradeIdsBySymbol = new Map(PHASE1_SYMBOLS.map((s) => [s.canonical, new BoundedIdSet(TRADE_ID_DEDUPE_WINDOW)]));

  const adapter = new BinanceAdapter({ logger });

  adapter.onTrade((trade) => {
    void (async () => {
      const seen = seenTradeIdsBySymbol.get(trade.symbol);
      const quality = evaluateTradeQuality(trade, seen ?? new Set(), new Date());
      const record = { ...trade, qualityStatus: quality.qualityStatus };
      seen?.add(trade.tradeId);

      await insertTrade(pool, record);
      if (quality.qualityStatus !== "rejected") {
        await publishJson(redis, tickChannel(trade.symbol), record);
      } else {
        logger.warn({ symbol: trade.symbol, reasons: quality.reasons }, "trade rejected by quality gate");
      }
    })().catch((error: unknown) => logger.error({ error: String(error) }, "failed to handle trade"));
  });

  adapter.onOhlcv((bar) => {
    void (async () => {
      const quality = evaluateOhlcvQuality(bar, new Date());
      const record = { ...bar, qualityStatus: quality.qualityStatus };

      await insertOhlcv(pool, record);
      if (quality.qualityStatus !== "rejected") {
        await publishJson(redis, ohlcvChannel(bar.symbol), record);
      } else {
        logger.warn({ symbol: bar.symbol, reasons: quality.reasons }, "ohlcv bar rejected by quality gate");
      }
    })().catch((error: unknown) => logger.error({ error: String(error) }, "failed to handle ohlcv bar"));
  });

  adapter.onOrderBookSnapshot((snapshot) => {
    void (async () => {
      const quality = evaluateOrderBookQuality(snapshot, new Date());
      const record = { ...snapshot, qualityStatus: quality.qualityStatus };

      await insertOrderBookSnapshot(pool, record);
      if (quality.qualityStatus !== "rejected") {
        await publishJson(redis, bookChannel(snapshot.symbol), record);
      } else {
        logger.warn({ symbol: snapshot.symbol, reasons: quality.reasons }, "order book snapshot rejected by quality gate");
      }
    })().catch((error: unknown) => logger.error({ error: String(error) }, "failed to handle order book snapshot"));
  });

  adapter.onError((error) => {
    logger.error({ error: error.message }, "market-data adapter error");
  });

  const futuresAdapter = new BinanceFuturesAdapter({ logger });

  futuresAdapter.onFundingRate((fundingRate) => {
    void (async () => {
      const quality = evaluateFundingRateQuality(fundingRate, new Date());
      const record = { ...fundingRate, qualityStatus: quality.qualityStatus };

      await insertFundingRate(pool, record);
      if (quality.qualityStatus !== "rejected") {
        await publishJson(redis, fundingRateChannel(fundingRate.symbol), record);
      } else {
        logger.warn({ symbol: fundingRate.symbol, reasons: quality.reasons }, "funding rate rejected by quality gate");
      }
    })().catch((error: unknown) => logger.error({ error: String(error) }, "failed to handle funding rate"));
  });

  futuresAdapter.onBasis((basis) => {
    void (async () => {
      const quality = evaluateBasisQuality(basis, new Date());
      const record = { ...basis, qualityStatus: quality.qualityStatus };

      await insertBasis(pool, record);
      if (quality.qualityStatus !== "rejected") {
        await publishJson(redis, basisChannel(basis.symbol), record);
      } else {
        logger.warn({ symbol: basis.symbol, reasons: quality.reasons }, "basis rejected by quality gate");
      }
    })().catch((error: unknown) => logger.error({ error: String(error) }, "failed to handle basis"));
  });

  futuresAdapter.onError((error) => {
    logger.error({ error: error.message }, "market-data futures adapter error");
  });

  adapter.connect();
  futuresAdapter.connect();
  logger.info({ symbols: PHASE1_SYMBOLS.map((s) => s.canonical) }, "market-data service started");

  const shutdown = async (): Promise<void> => {
    logger.info("shutting down market-data service");
    adapter.disconnect();
    futuresAdapter.disconnect();
    await redis.quit();
    await pool.end();
    process.exit(0);
  };
  process.on("SIGINT", () => void shutdown());
  process.on("SIGTERM", () => void shutdown());
}

main().catch((error: unknown) => {
  console.error("market-data service failed to start:", error);
  process.exit(1);
});
