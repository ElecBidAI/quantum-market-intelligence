/**
 * Live push updates for the dashboard. services/market-data publishes
 * accepted (non-"rejected") records to these Redis channels
 * (services/market-data/src/publish.ts) — the names must match exactly.
 */
export type MarketEventType = "tick" | "ohlcv" | "book";

export interface ChannelSubscription {
  type: MarketEventType;
  channel: string;
}

export function buildSymbolChannels(symbol: string): ChannelSubscription[] {
  return [
    { type: "tick", channel: `qmi:ticks:${symbol}` },
    { type: "ohlcv", channel: `qmi:ohlcv:${symbol}` },
    { type: "book", channel: `qmi:book:${symbol}` },
  ];
}

/** Minimal shape apps/api needs from a Redis subscriber — tests inject a fake. */
export interface PubSub {
  subscribe(channel: string, onMessage: (message: string) => void): Promise<void>;
  unsubscribe(channel: string): Promise<void>;
}

export class RedisPubSub implements PubSub {
  constructor(
    private readonly subscriber: {
      subscribe(channel: string, listener: (message: string) => void): Promise<void>;
      unsubscribe(channel: string): Promise<void>;
    },
  ) {}

  subscribe(channel: string, onMessage: (message: string) => void): Promise<void> {
    return this.subscriber.subscribe(channel, onMessage);
  }

  unsubscribe(channel: string): Promise<void> {
    return this.subscriber.unsubscribe(channel);
  }
}
