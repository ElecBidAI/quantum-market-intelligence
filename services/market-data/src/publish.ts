import type { RedisClientType } from "redis";

/**
 * Channel naming for live push updates. apps/api subscribes to these and
 * relays them to the dashboard over SSE (see apps/api/src/market-stream.ts).
 * Redis is ephemeral fan-out only — Postgres (packages persistence.ts) is
 * the durable source of truth.
 */
export function tickChannel(symbol: string): string {
  return `qmi:ticks:${symbol}`;
}
export function ohlcvChannel(symbol: string): string {
  return `qmi:ohlcv:${symbol}`;
}
export function bookChannel(symbol: string): string {
  return `qmi:book:${symbol}`;
}
export function fundingRateChannel(symbol: string): string {
  return `qmi:funding:${symbol}`;
}
export function basisChannel(symbol: string): string {
  return `qmi:basis:${symbol}`;
}

export async function publishJson(
  redis: Pick<RedisClientType, "publish">,
  channel: string,
  payload: unknown,
): Promise<void> {
  await redis.publish(channel, JSON.stringify(payload));
}
