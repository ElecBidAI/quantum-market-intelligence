/**
 * Pure state-merging logic for the live dashboard, kept separate from the
 * React/EventSource plumbing (MarketDashboard.tsx) so it's unit-testable
 * without a DOM. Never invents a value: a field stays null until a real
 * message (initial /market/latest fetch or a live SSE event) supplies it —
 * see brief Section 18, "Never fabricate live data."
 */

export interface LatestBar {
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SymbolMarketState {
  symbol: string;
  exchange: string | null;
  lastPrice: number | null;
  lastBar: LatestBar | null;
  lastUpdate: string | null;
}

export type MarketState = Record<string, SymbolMarketState>;

export function initMarketState(symbols: readonly string[]): MarketState {
  const state: MarketState = {};
  for (const symbol of symbols) {
    state[symbol] = { symbol, exchange: null, lastPrice: null, lastBar: null, lastUpdate: null };
  }
  return state;
}

interface LatestSnapshotEntry {
  symbol: string;
  trade: { exchange: string; price: number; timestamp: string } | null;
  bar: {
    exchange: string;
    interval: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    timestamp: string;
  } | null;
}

/** Applies the initial GET /market/latest response over the current state. */
export function applyLatestSnapshot(state: MarketState, entries: readonly LatestSnapshotEntry[]): MarketState {
  const next = { ...state };
  for (const entry of entries) {
    const current = next[entry.symbol] ?? {
      symbol: entry.symbol,
      exchange: null,
      lastPrice: null,
      lastBar: null,
      lastUpdate: null,
    };
    const bothTimestamps = [entry.trade?.timestamp, entry.bar?.timestamp].filter(
      (t): t is string => typeof t === "string",
    );
    const lastUpdate = bothTimestamps.sort().at(-1) ?? current.lastUpdate;

    next[entry.symbol] = {
      symbol: entry.symbol,
      exchange: entry.trade?.exchange ?? entry.bar?.exchange ?? current.exchange,
      lastPrice: entry.trade?.price ?? current.lastPrice,
      lastBar: entry.bar
        ? {
            interval: entry.bar.interval,
            open: entry.bar.open,
            high: entry.bar.high,
            low: entry.bar.low,
            close: entry.bar.close,
            volume: entry.bar.volume,
          }
        : current.lastBar,
      lastUpdate,
    };
  }
  return next;
}

interface TickEvent {
  symbol: string;
  exchange: string;
  price: number;
  timestamp: string;
}

export function applyTickEvent(state: MarketState, tick: TickEvent): MarketState {
  const current = state[tick.symbol];
  if (!current) return state;
  return {
    ...state,
    [tick.symbol]: {
      ...current,
      exchange: tick.exchange,
      lastPrice: tick.price,
      lastUpdate: tick.timestamp,
    },
  };
}

interface OhlcvEvent {
  symbol: string;
  exchange: string;
  interval: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  timestamp: string;
}

export function applyOhlcvEvent(state: MarketState, bar: OhlcvEvent): MarketState {
  const current = state[bar.symbol];
  if (!current) return state;
  return {
    ...state,
    [bar.symbol]: {
      ...current,
      exchange: bar.exchange,
      lastBar: {
        interval: bar.interval,
        open: bar.open,
        high: bar.high,
        low: bar.low,
        close: bar.close,
        volume: bar.volume,
      },
      lastUpdate: bar.timestamp,
    },
  };
}

const STALE_AFTER_MS = 30_000;

/** Whether a symbol's last update is recent enough to call the feed "live" (see quality.ts's STALE_THRESHOLD_MS on the ingestion side). */
export function isLive(lastUpdate: string | null, now: Date): boolean {
  if (!lastUpdate) return false;
  return now.getTime() - new Date(lastUpdate).getTime() <= STALE_AFTER_MS;
}
