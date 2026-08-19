import { z } from "zod";
import { envelope } from "./common.js";

/** Trade / tick (docs/architecture/DATA-CONTRACTS.md Section 3.1). */
export const trade = envelope.extend({
  price: z.number().positive(),
  size: z.number().positive(),
  side: z.enum(["buy", "sell", "unknown"]),
  tradeId: z.string().min(1),
});
export type Trade = z.infer<typeof trade>;

/** OHLCV bar (docs/architecture/DATA-CONTRACTS.md Section 3.2). */
export const ohlcv = envelope
  .extend({
    interval: z.string().min(1),
    open: z.number().nonnegative(),
    high: z.number().nonnegative(),
    low: z.number().nonnegative(),
    close: z.number().nonnegative(),
    volume: z.number().nonnegative(),
  })
  .refine((bar) => bar.high >= bar.low, {
    message: "high must be >= low",
    path: ["high"],
  })
  .refine((bar) => bar.high >= bar.open && bar.high >= bar.close, {
    message: "high must be >= open and close",
    path: ["high"],
  })
  .refine((bar) => bar.low <= bar.open && bar.low <= bar.close, {
    message: "low must be <= open and close",
    path: ["low"],
  });
export type Ohlcv = z.infer<typeof ohlcv>;

/** Best bid/ask quote (docs/architecture/DATA-CONTRACTS.md Section 3.3). */
export const quote = envelope.extend({
  bidPrice: z.number().nonnegative(),
  bidSize: z.number().nonnegative(),
  askPrice: z.number().nonnegative(),
  askSize: z.number().nonnegative(),
});
export type Quote = z.infer<typeof quote>;

const priceLevel = z.tuple([z.number().nonnegative(), z.number().nonnegative()]);

/** Order-book snapshot (docs/architecture/DATA-CONTRACTS.md Section 3.4). */
export const orderBookSnapshot = envelope.extend({
  bids: z.array(priceLevel),
  asks: z.array(priceLevel),
  sequenceId: z.number().int().nonnegative(),
});
export type OrderBookSnapshot = z.infer<typeof orderBookSnapshot>;

/** Order-book delta (docs/architecture/DATA-CONTRACTS.md Section 3.5). */
export const orderBookDelta = envelope.extend({
  side: z.enum(["bid", "ask"]),
  price: z.number().nonnegative(),
  size: z.number().nonnegative(),
  sequenceId: z.number().int().nonnegative(),
  previousSequenceId: z.number().int().nonnegative(),
});
export type OrderBookDelta = z.infer<typeof orderBookDelta>;
