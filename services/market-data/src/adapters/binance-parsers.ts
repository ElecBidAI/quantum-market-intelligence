import type { Ohlcv, OrderBookSnapshot, Trade } from "@qmi/contracts";
import { toCanonicalSymbol } from "../symbols.js";

export const BINANCE_EXCHANGE = "binance";
export const BINANCE_SOURCE = "binance-ws";
const SCHEMA_VERSION = 1;

class MalformedMessageError extends Error {
  constructor(streamKind: string, reason: string) {
    super(`malformed Binance ${streamKind} message: ${reason}`);
    this.name = "MalformedMessageError";
  }
}

function requireString(value: unknown, field: string, streamKind: string): string {
  if (typeof value !== "string" || value.length === 0) {
    throw new MalformedMessageError(streamKind, `expected non-empty string field "${field}"`);
  }
  return value;
}

function requireNumber(value: unknown, field: string, streamKind: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new MalformedMessageError(streamKind, `expected finite number field "${field}"`);
  }
  return value;
}

function requireNumericString(value: unknown, field: string, streamKind: string): number {
  const raw = requireString(value, field, streamKind);
  const parsed = Number(raw);
  if (!Number.isFinite(parsed)) {
    throw new MalformedMessageError(streamKind, `field "${field}" is not numeric: "${raw}"`);
  }
  return parsed;
}

function resolveCanonicalSymbol(binanceSymbol: string, streamKind: string): string {
  const canonical = toCanonicalSymbol(binanceSymbol);
  if (!canonical) {
    throw new MalformedMessageError(streamKind, `unknown symbol "${binanceSymbol}"`);
  }
  return canonical;
}

/**
 * Parses a Binance `<symbol>@trade` payload into a Trade contract record.
 * `m` (isBuyerMaker) true means the resting order was a buy, so the
 * aggressor (taker) side was a sell, and vice versa.
 */
export function parseTradeMessage(data: unknown, now: () => Date = () => new Date()): Trade {
  const kind = "trade";
  if (typeof data !== "object" || data === null) {
    throw new MalformedMessageError(kind, "payload is not an object");
  }
  const d = data as Record<string, unknown>;

  const symbol = resolveCanonicalSymbol(requireString(d.s, "s", kind), kind);
  const price = requireNumericString(d.p, "p", kind);
  const size = requireNumericString(d.q, "q", kind);
  const tradeTime = requireNumber(d.T, "T", kind);
  const tradeId = String(requireNumber(d.t, "t", kind));
  const isBuyerMaker = d.m;
  if (typeof isBuyerMaker !== "boolean") {
    throw new MalformedMessageError(kind, 'expected boolean field "m"');
  }

  return {
    source: BINANCE_SOURCE,
    exchange: BINANCE_EXCHANGE,
    symbol,
    timestamp: new Date(tradeTime).toISOString(),
    ingestedAt: now().toISOString(),
    qualityStatus: "ok",
    schemaVersion: SCHEMA_VERSION,
    price,
    size,
    side: isBuyerMaker ? "sell" : "buy",
    tradeId,
  };
}

/**
 * Parses a Binance `<symbol>@kline_1m` payload into an Ohlcv contract
 * record. Returns null when the bar is still open (`k.x === false`) —
 * services/market-data never persists an in-progress bar as final.
 */
export function parseKlineMessage(data: unknown, now: () => Date = () => new Date()): Ohlcv | null {
  const kind = "kline";
  if (typeof data !== "object" || data === null) {
    throw new MalformedMessageError(kind, "payload is not an object");
  }
  const d = data as Record<string, unknown>;
  const k = d.k;
  if (typeof k !== "object" || k === null) {
    throw new MalformedMessageError(kind, 'expected object field "k"');
  }
  const kd = k as Record<string, unknown>;

  const isClosed = kd.x;
  if (typeof isClosed !== "boolean") {
    throw new MalformedMessageError(kind, 'expected boolean field "k.x"');
  }
  if (!isClosed) {
    return null;
  }

  const symbol = resolveCanonicalSymbol(requireString(kd.s, "k.s", kind), kind);
  const interval = requireString(kd.i, "k.i", kind);
  const closeTime = requireNumber(kd.T, "k.T", kind);
  const open = requireNumericString(kd.o, "k.o", kind);
  const high = requireNumericString(kd.h, "k.h", kind);
  const low = requireNumericString(kd.l, "k.l", kind);
  const close = requireNumericString(kd.c, "k.c", kind);
  const volume = requireNumericString(kd.v, "k.v", kind);

  return {
    source: BINANCE_SOURCE,
    exchange: BINANCE_EXCHANGE,
    symbol,
    timestamp: new Date(closeTime).toISOString(),
    ingestedAt: now().toISOString(),
    qualityStatus: "ok",
    schemaVersion: SCHEMA_VERSION,
    interval,
    open,
    high,
    low,
    close,
    volume,
  };
}

/**
 * Parses a Binance `<symbol>@depth20@100ms` partial-book-depth payload into
 * an OrderBookSnapshot contract record. This stream already sends the full
 * top-N book on every update (not a delta), so no sequence-gap
 * reconstruction is needed for it — see the note in
 * data/migrations/0002_market_data.sql about orderbook_deltas being
 * deferred to a later phase.
 */
export function parseDepthSnapshotMessage(
  data: unknown,
  binanceSymbol: string,
  now: () => Date = () => new Date(),
): OrderBookSnapshot {
  const kind = "depth";
  if (typeof data !== "object" || data === null) {
    throw new MalformedMessageError(kind, "payload is not an object");
  }
  const d = data as Record<string, unknown>;

  const symbol = resolveCanonicalSymbol(binanceSymbol, kind);
  const sequenceId = requireNumber(d.lastUpdateId, "lastUpdateId", kind);
  const bids = parsePriceLevels(d.bids, "bids", kind);
  const asks = parsePriceLevels(d.asks, "asks", kind);

  return {
    source: BINANCE_SOURCE,
    exchange: BINANCE_EXCHANGE,
    symbol,
    timestamp: now().toISOString(),
    ingestedAt: now().toISOString(),
    qualityStatus: "ok",
    schemaVersion: SCHEMA_VERSION,
    bids,
    asks,
    sequenceId,
  };
}

function parsePriceLevels(value: unknown, field: string, streamKind: string): Array<[number, number]> {
  if (!Array.isArray(value)) {
    throw new MalformedMessageError(streamKind, `expected array field "${field}"`);
  }
  return value.map((level, index) => {
    if (!Array.isArray(level) || level.length !== 2) {
      throw new MalformedMessageError(streamKind, `"${field}[${index}]" is not a [price, size] pair`);
    }
    const price = Number(level[0]);
    const size = Number(level[1]);
    if (!Number.isFinite(price) || !Number.isFinite(size)) {
      throw new MalformedMessageError(streamKind, `"${field}[${index}]" has a non-numeric price/size`);
    }
    return [price, size];
  });
}
