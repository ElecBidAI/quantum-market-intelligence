import type { Ohlcv, OrderBookSnapshot, QualityStatus, Trade } from "@qmi/contracts";

/**
 * Data-quality gates (docs/architecture/DATA-CONTRACTS.md Section 8). These
 * never mutate or impute a value — they only classify a record's
 * qualityStatus and attach machine-readable reason codes. A record that
 * fails a gate is still persisted, marked "suspect" or "rejected", so the
 * failure is auditable instead of silently disappearing.
 */
export interface QualityResult {
  qualityStatus: QualityStatus;
  reasons: string[];
}

const OK: QualityResult = { qualityStatus: "ok", reasons: [] };

export const STALE_THRESHOLD_MS = 30_000;
export const FUTURE_TOLERANCE_MS = 5_000;

function checkTimestampSanity(timestamp: string, now: Date): QualityResult | null {
  const eventTime = new Date(timestamp).getTime();
  const ageMs = now.getTime() - eventTime;
  if (ageMs > STALE_THRESHOLD_MS) {
    return { qualityStatus: "suspect", reasons: ["STALE_FEED"] };
  }
  if (ageMs < -FUTURE_TOLERANCE_MS) {
    return { qualityStatus: "suspect", reasons: ["ABNORMAL_TIMESTAMP_FUTURE"] };
  }
  return null;
}

/** Read-only membership check, satisfied by both Set and BoundedIdSet. */
export interface SeenIdLookup {
  has(id: string): boolean;
}

/**
 * Evaluates a trade for staleness and duplication. `seenTradeIds` is a
 * caller-owned, bounded set (e.g. per-symbol ring buffer) so this function
 * stays pure and side-effect-free with respect to time/dedupe state.
 */
export function evaluateTradeQuality(
  trade: Trade,
  seenTradeIds: SeenIdLookup,
  now: Date = new Date(),
): QualityResult {
  if (seenTradeIds.has(trade.tradeId)) {
    return { qualityStatus: "rejected", reasons: ["DUPLICATE_TICK"] };
  }
  const timestampIssue = checkTimestampSanity(trade.timestamp, now);
  if (timestampIssue) return timestampIssue;
  return OK;
}

export function evaluateOhlcvQuality(bar: Ohlcv, now: Date = new Date()): QualityResult {
  const timestampIssue = checkTimestampSanity(bar.timestamp, now);
  if (timestampIssue) return timestampIssue;
  return OK;
}

export function evaluateOrderBookQuality(
  snapshot: OrderBookSnapshot,
  now: Date = new Date(),
): QualityResult {
  const bestBid = snapshot.bids[0]?.[0];
  const bestAsk = snapshot.asks[0]?.[0];
  if (bestBid !== undefined && bestAsk !== undefined && bestBid >= bestAsk) {
    return { qualityStatus: "rejected", reasons: ["CROSSED_BOOK"] };
  }
  const timestampIssue = checkTimestampSanity(snapshot.timestamp, now);
  if (timestampIssue) return timestampIssue;
  return OK;
}

/** Bounded FIFO set used to dedupe recent trade IDs per symbol without unbounded memory growth. */
export class BoundedIdSet {
  private readonly ids = new Set<string>();
  private readonly order: string[] = [];

  constructor(private readonly capacity: number) {}

  has(id: string): boolean {
    return this.ids.has(id);
  }

  add(id: string): void {
    if (this.ids.has(id)) return;
    this.ids.add(id);
    this.order.push(id);
    if (this.order.length > this.capacity) {
      const oldest = this.order.shift();
      if (oldest !== undefined) this.ids.delete(oldest);
    }
  }
}
