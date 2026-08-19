import { z } from "zod";
import { envelope } from "./common.js";

/**
 * Derivatives contracts (docs/architecture/DATA-CONTRACTS.md Section 4).
 * Implemented now that Phase 9 (Derivatives Engine) has a producer for
 * them — see services/market-data/src/adapters/binance-futures.ts.
 */

/** Funding rate (perpetual futures). */
export const fundingRate = envelope.extend({
  rate: z.number(),
  intervalHours: z.number().positive(),
});
export type FundingRate = z.infer<typeof fundingRate>;

/** Open interest. Reserved: no ingestion pipeline yet (see that adapter's README). */
export const openInterest = envelope.extend({
  openInterest: z.number().nonnegative(),
  notional: z.number().nonnegative(),
});
export type OpenInterest = z.infer<typeof openInterest>;

/** Futures-vs-spot basis. */
export const basis = envelope.extend({
  spotPrice: z.number().positive(),
  futuresPrice: z.number().positive(),
  basis: z.number(),
  annualizedBasis: z.number(),
});
export type Basis = z.infer<typeof basis>;

/** Liquidation event. Reserved: no ingestion pipeline yet. */
export const liquidationEvent = envelope.extend({
  side: z.enum(["long", "short"]),
  price: z.number().positive(),
  size: z.number().positive(),
});
export type LiquidationEvent = z.infer<typeof liquidationEvent>;

/** A single point on a futures curve (one expiry's price). Reserved: no ingestion pipeline yet. */
export const futuresCurvePoint = envelope.extend({
  expiry: z.string(),
  price: z.number().positive(),
});
export type FuturesCurvePoint = z.infer<typeof futuresCurvePoint>;
