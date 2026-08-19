import { describe, expect, it, vi } from "vitest";
import { buildSymbolChannels, RedisPubSub } from "../src/market-stream.js";

describe("buildSymbolChannels", () => {
  it("builds tick/ohlcv/book channels matching services/market-data's publish.ts naming", () => {
    expect(buildSymbolChannels("BTC-USDT")).toEqual([
      { type: "tick", channel: "qmi:ticks:BTC-USDT" },
      { type: "ohlcv", channel: "qmi:ohlcv:BTC-USDT" },
      { type: "book", channel: "qmi:book:BTC-USDT" },
    ]);
  });
});

describe("RedisPubSub", () => {
  it("delegates subscribe to the underlying client", async () => {
    const subscribe = vi.fn().mockResolvedValue(undefined);
    const unsubscribe = vi.fn().mockResolvedValue(undefined);
    const pubsub = new RedisPubSub({ subscribe, unsubscribe });

    const onMessage = () => {};
    await pubsub.subscribe("qmi:ticks:BTC-USDT", onMessage);

    expect(subscribe).toHaveBeenCalledWith("qmi:ticks:BTC-USDT", onMessage);
  });

  it("delegates unsubscribe to the underlying client", async () => {
    const subscribe = vi.fn().mockResolvedValue(undefined);
    const unsubscribe = vi.fn().mockResolvedValue(undefined);
    const pubsub = new RedisPubSub({ subscribe, unsubscribe });

    await pubsub.unsubscribe("qmi:ticks:BTC-USDT");

    expect(unsubscribe).toHaveBeenCalledWith("qmi:ticks:BTC-USDT");
  });
});
