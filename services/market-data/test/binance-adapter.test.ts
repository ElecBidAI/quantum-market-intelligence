import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createLogger } from "@qmi/observability";
import { BinanceAdapter } from "../src/adapters/binance.js";

type Listener = (event: unknown) => void;

/** Minimal fake WebSocket so tests never touch the network. */
class FakeWebSocket {
  static instances: FakeWebSocket[] = [];
  readonly url: string;
  private listeners = new Map<string, Listener[]>();
  closeCalled = false;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  addEventListener(type: string, listener: Listener): void {
    const list = this.listeners.get(type) ?? [];
    list.push(listener);
    this.listeners.set(type, list);
  }

  close(): void {
    this.closeCalled = true;
  }

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

describe("BinanceAdapter", () => {
  it("connects to a stream URL covering BTC and ETH trade/kline/depth streams", () => {
    const adapter = new BinanceAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    adapter.connect();

    expect(FakeWebSocket.instances).toHaveLength(1);
    const url = FakeWebSocket.instances[0]!.url;
    expect(url).toContain("btcusdt@trade");
    expect(url).toContain("btcusdt@kline_1m");
    expect(url).toContain("btcusdt@depth20@100ms");
    expect(url).toContain("ethusdt@trade");
    expect(url).toContain("ethusdt@kline_1m");
    expect(url).toContain("ethusdt@depth20@100ms");
  });

  it("routes a trade message to onTrade handlers", () => {
    const adapter = new BinanceAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    const received: unknown[] = [];
    adapter.onTrade((trade) => received.push(trade));
    adapter.connect();

    const socket = FakeWebSocket.instances[0]!;
    socket.emit("message", {
      data: JSON.stringify({
        stream: "btcusdt@trade",
        data: { s: "BTCUSDT", t: 1, p: "65000", q: "0.01", T: 1755604800000, m: false },
      }),
    });

    expect(received).toHaveLength(1);
    expect((received[0] as { symbol: string }).symbol).toBe("BTC-USDT");
  });

  it("emits an error and does not crash on non-JSON messages", () => {
    const adapter = new BinanceAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    const errors: Error[] = [];
    adapter.onError((error) => errors.push(error));
    adapter.connect();

    const socket = FakeWebSocket.instances[0]!;
    expect(() => socket.emit("message", { data: "not json" })).not.toThrow();
    expect(errors).toHaveLength(1);
    expect(errors[0]!.message).toMatch(/non-JSON/);
  });

  it("emits an error for a malformed but valid-JSON trade payload instead of throwing", () => {
    const adapter = new BinanceAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    const errors: Error[] = [];
    adapter.onError((error) => errors.push(error));
    adapter.connect();

    const socket = FakeWebSocket.instances[0]!;
    socket.emit("message", {
      data: JSON.stringify({ stream: "btcusdt@trade", data: { s: "BTCUSDT" } }),
    });

    expect(errors).toHaveLength(1);
    expect(errors[0]!.message).toMatch(/malformed/);
  });

  it("schedules a reconnect with backoff after an unexpected close", () => {
    const adapter = new BinanceAdapter({
      logger: silentLogger(),
      createSocket: (url) => new FakeWebSocket(url) as unknown as WebSocket,
    });
    adapter.connect();
    expect(FakeWebSocket.instances).toHaveLength(1);

    FakeWebSocket.instances[0]!.emit("close");
    expect(FakeWebSocket.instances).toHaveLength(1); // not reconnected yet

    vi.advanceTimersByTime(1000); // first backoff delay
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it("does not reconnect after an explicit disconnect", () => {
    const adapter = new BinanceAdapter({
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
