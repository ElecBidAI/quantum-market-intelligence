import type { Basis, FundingRate } from "@qmi/contracts";
import {
  BINANCE_EXCHANGE,
  MalformedMessageError,
  requireNumber,
  requireNumericString,
  requireString,
  resolveCanonicalSymbol,
} from "./binance-parsers.js";

export const BINANCE_FUTURES_SOURCE = "binance-futures-ws";
const SCHEMA_VERSION = 1;

// Binance perpetuals fund every 8 hours (3x/day) for every symbol this
// service ingests. If that ever changes per-symbol, this becomes a
// per-symbol lookup instead of a constant — not worth the complexity until
// there's a symbol where it's actually true.
export const FUNDING_INTERVAL_HOURS = 8;

/**
 * Parses a Binance USDT-M Futures `<symbol>@markPrice@1s` payload into a
 * FundingRate contract record.
 */
export function parseFundingRateMessage(
  data: unknown,
  now: () => Date = () => new Date(),
): FundingRate {
  const kind = "markPrice";
  if (typeof data !== "object" || data === null) {
    throw new MalformedMessageError(kind, "payload is not an object");
  }
  const d = data as Record<string, unknown>;

  const symbol = resolveCanonicalSymbol(requireString(d.s, "s", kind), kind);
  const rate = requireNumericString(d.r, "r", kind);
  const eventTime = requireNumber(d.E, "E", kind);

  return {
    source: BINANCE_FUTURES_SOURCE,
    exchange: BINANCE_EXCHANGE,
    symbol,
    timestamp: new Date(eventTime).toISOString(),
    ingestedAt: now().toISOString(),
    qualityStatus: "ok",
    schemaVersion: SCHEMA_VERSION,
    rate,
    intervalHours: FUNDING_INTERVAL_HOURS,
  };
}

/**
 * Parses the same `markPrice` payload into a Basis contract record, using
 * Binance's index price (`i`) as the spot-price reference — that's exactly
 * what the index price is: the spot-market composite the perpetual's
 * funding mechanism targets. `annualizedBasis` is left as the raw basis
 * percentage (not scaled) — see quant_core.derivatives' module docstring:
 * perpetuals have no expiry to annualize against the way a dated future
 * does; the economically meaningful "annualized" figure for a perpetual is
 * `quant_core.derivatives.annualized_funding_rate`, computed from the
 * funding rate this same message carries, not from the basis.
 */
export function parseBasisMessage(data: unknown, now: () => Date = () => new Date()): Basis {
  const kind = "markPrice";
  if (typeof data !== "object" || data === null) {
    throw new MalformedMessageError(kind, "payload is not an object");
  }
  const d = data as Record<string, unknown>;

  const symbol = resolveCanonicalSymbol(requireString(d.s, "s", kind), kind);
  const futuresPrice = requireNumericString(d.p, "p", kind);
  const spotPrice = requireNumericString(d.i, "i", kind);
  const eventTime = requireNumber(d.E, "E", kind);
  const basisValue = futuresPrice - spotPrice;

  return {
    source: BINANCE_FUTURES_SOURCE,
    exchange: BINANCE_EXCHANGE,
    symbol,
    timestamp: new Date(eventTime).toISOString(),
    ingestedAt: now().toISOString(),
    qualityStatus: "ok",
    schemaVersion: SCHEMA_VERSION,
    spotPrice,
    futuresPrice,
    basis: basisValue,
    annualizedBasis: basisValue / spotPrice,
  };
}
