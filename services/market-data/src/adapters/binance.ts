import type { Ohlcv, OrderBookSnapshot, Trade } from "@qmi/contracts";
import type { Logger } from "@qmi/observability";
import type { ExchangeAdapter } from "../exchange-adapter.js";
import { computeBackoffDelayMs, DEFAULT_BACKOFF } from "../reconnect.js";
import { PHASE1_SYMBOLS } from "../symbols.js";
import { BINANCE_EXCHANGE, parseDepthSnapshotMessage, parseKlineMessage, parseTradeMessage } from "./binance-parsers.js";

const STREAM_BASE_URL = "wss://stream.binance.com:9443/stream";
const KLINE_INTERVAL = "1m";
const DEPTH_LEVELS = 20;
const DEPTH_UPDATE_SPEED = "100ms";

function buildStreamUrl(symbols: readonly { binance: string }[]): string {
  const streams = symbols.flatMap((s) => [
    `${s.binance}@trade`,
    `${s.binance}@kline_${KLINE_INTERVAL}`,
    `${s.binance}@depth${DEPTH_LEVELS}@${DEPTH_UPDATE_SPEED}`,
  ]);
  return `${STREAM_BASE_URL}?streams=${streams.join("/")}`;
}

/** Extracts the Binance wire symbol from a combined-stream `stream` field, e.g. "btcusdt@trade" -> "btcusdt". */
function symbolFromStreamName(streamName: string): string {
  const separatorIndex = streamName.indexOf("@");
  return separatorIndex === -1 ? streamName : streamName.slice(0, separatorIndex);
}

export interface BinanceAdapterOptions {
  logger: Logger;
  symbols?: readonly { canonical: string; binance: string }[];
  /** Injectable for tests; defaults to the global WebSocket client. */
  createSocket?: (url: string) => WebSocket;
}

/**
 * Binance spot market-data adapter: the first implementation of
 * ExchangeAdapter (docs/architecture/QMI-MASTER-ARCHITECTURE.md Section 5).
 * Public market-data streams only — no API key, no order placement
 * capability exists in this class.
 */
export class BinanceAdapter implements ExchangeAdapter {
  readonly exchangeName = BINANCE_EXCHANGE;

  private readonly logger: Logger;
  private readonly symbols: readonly { canonical: string; binance: string }[];
  private readonly createSocket: (url: string) => WebSocket;

  private socket: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closedByCaller = false;

  private tradeHandlers: Array<(trade: Trade) => void> = [];
  private ohlcvHandlers: Array<(bar: Ohlcv) => void> = [];
  private orderBookHandlers: Array<(snapshot: OrderBookSnapshot) => void> = [];
  private errorHandlers: Array<(error: Error) => void> = [];

  constructor(options: BinanceAdapterOptions) {
    this.logger = options.logger;
    this.symbols = options.symbols ?? PHASE1_SYMBOLS;
    this.createSocket = options.createSocket ?? ((url) => new WebSocket(url));
  }

  onTrade(handler: (trade: Trade) => void): void {
    this.tradeHandlers.push(handler);
  }

  onOhlcv(handler: (bar: Ohlcv) => void): void {
    this.ohlcvHandlers.push(handler);
  }

  onOrderBookSnapshot(handler: (snapshot: OrderBookSnapshot) => void): void {
    this.orderBookHandlers.push(handler);
  }

  onError(handler: (error: Error) => void): void {
    this.errorHandlers.push(handler);
  }

  connect(): void {
    this.closedByCaller = false;
    this.openSocket();
  }

  disconnect(): void {
    this.closedByCaller = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }

  private openSocket(): void {
    const url = buildStreamUrl(this.symbols);
    const socket = this.createSocket(url);
    this.socket = socket;

    socket.addEventListener("open", () => {
      this.reconnectAttempt = 0;
      this.logger.info({ exchange: this.exchangeName }, "market-data websocket connected");
    });

    socket.addEventListener("message", (event: MessageEvent) => {
      this.handleMessage(event.data);
    });

    socket.addEventListener("error", () => {
      this.emitError(new Error("websocket error"));
    });

    socket.addEventListener("close", () => {
      this.logger.warn({ exchange: this.exchangeName }, "market-data websocket closed");
      if (!this.closedByCaller) {
        this.scheduleReconnect();
      }
    });
  }

  private scheduleReconnect(): void {
    const delay = computeBackoffDelayMs(this.reconnectAttempt, DEFAULT_BACKOFF);
    this.reconnectAttempt += 1;
    this.logger.info({ exchange: this.exchangeName, delayMs: delay }, "scheduling market-data reconnect");
    this.reconnectTimer = setTimeout(() => {
      if (!this.closedByCaller) this.openSocket();
    }, delay);
  }

  private handleMessage(raw: unknown): void {
    let envelope: unknown;
    try {
      envelope = JSON.parse(String(raw));
    } catch {
      this.emitError(new Error("received non-JSON websocket message"));
      return;
    }

    if (typeof envelope !== "object" || envelope === null) {
      this.emitError(new Error("websocket message envelope is not an object"));
      return;
    }
    const { stream, data } = envelope as Record<string, unknown>;
    if (typeof stream !== "string") {
      this.emitError(new Error('websocket message envelope missing "stream" field'));
      return;
    }

    try {
      if (stream.endsWith("@trade")) {
        const trade = parseTradeMessage(data);
        this.tradeHandlers.forEach((h) => h(trade));
      } else if (stream.includes("@kline_")) {
        const bar = parseKlineMessage(data);
        if (bar) this.ohlcvHandlers.forEach((h) => h(bar));
      } else if (stream.includes("@depth")) {
        const binanceSymbol = symbolFromStreamName(stream);
        const snapshot = parseDepthSnapshotMessage(data, binanceSymbol);
        this.orderBookHandlers.forEach((h) => h(snapshot));
      }
    } catch (error) {
      this.emitError(error instanceof Error ? error : new Error(String(error)));
    }
  }

  private emitError(error: Error): void {
    this.logger.warn({ exchange: this.exchangeName, error: error.message }, "market-data adapter error");
    this.errorHandlers.forEach((h) => h(error));
  }
}
