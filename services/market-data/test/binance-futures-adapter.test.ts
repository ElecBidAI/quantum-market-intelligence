import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createLogger } from "@qmi/observability";
import { BinanceFuturesAdapter } from "../src/adapters/binance-futures.js";

type Listener = (event: unknown) => void;

/** Minimal fake WebSocket so tests never touch the network. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  readonly url: string;
  private listeners = new Map<string, Listener[]>();

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  }

  close(): void {}

  emit(type: string, event: unknown = {}): void {
    for (const listener of this.listeners.get(type) ?? []) listener(event);
  }
}

function silentLogger() {
  return createLogger({ service: "test", level: "fatal" });
}

beforeEach(() => {
  FakeWebSocket.instances = [];
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

const validMarkPrice = {
  e: "markPriceUpdate",
  E: 1755604800000,
  s: "BTCUSDT",
  p: "65200.50",
  i: "65000.00",
  r: "0.00010000",
  T: 1755633600000,
};

describe("BinanceFuturesAdapter", () => {
  it("connects to a markPrice stream URL covering BTC and ETH", () => {
    const adapter = new BinanceFuturesAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    adapter.connect();

    expect(FakeWebSocket.instances).toHaveLength(1);
    const url = FakeWebSocket.instances[0]!.url;
    expect(url).toContain("fstream.binance.com");
    expect(url).toContain("btcusdt@markPrice@1s");
    expect(url).toContain("ethusdt@markPrice@1s");
  });

  it("routes a markPrice message to both funding-rate and basis handlers", () => {
    const adapter = new BinanceFuturesAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    const fundingRates: unknown[] = [];
    const bases: unknown[] = [];
    adapter.onFundingRate((r) => fundingRates.push(r));
    adapter.onBasis((b) => bases.push(b));
    adapter.connect();

    const socket = FakeWebSocket.instances[0]!;
    socket.emit("message", {
      data: JSON.stringify({ stream: "btcusdt@markPrice@1s", data: validMarkPrice }),
    });

    expect(fundingRates).toHaveLength(1);
    expect((fundingRates[0] as { symbol: string }).symbol).toBe("BTC-USDT");
    expect(bases).toHaveLength(1);
    expect((bases[0] as { symbol: string }).symbol).toBe("BTC-USDT");
  });

  it("emits an error for a malformed markPrice payload instead of throwing", () => {
    const adapter = new BinanceFuturesAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    const errors: Error[] = [];
    adapter.onError((error) => errors.push(error));
    adapter.connect();

    const socket = FakeWebSocket.instances[0]!;
    socket.emit("message", {
      data: JSON.stringify({ stream: "btcusdt@markPrice@1s", data: { s: "BTCUSDT" } }),
    });

    expect(errors).toHaveLength(1);
    expect(errors[0]!.message).toMatch(/malformed/);
  });

  it("schedules a reconnect with backoff after an unexpected close", () => {
    const adapter = new BinanceFuturesAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    adapter.connect();
    expect(FakeWebSocket.instances).toHaveLength(1);

    FakeWebSocket.instances[0]!.emit("close");
    expect(FakeWebSocket.instances).toHaveLength(1);

    vi.advanceTimersByTime(1000);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("does not reconnect after an explicit disconnect", () => {
    const adapter = new BinanceFuturesAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    adapter.connect();
    adapter.disconnect();
    FakeWebSocket.instances[0]!.emit("close");

    vi.advanceTimersByTime(60_000);
    expect(FakeWebSocket.instances).toHaveLength(1);
  });
});
