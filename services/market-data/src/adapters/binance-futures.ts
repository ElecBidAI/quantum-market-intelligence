import type { Basis, FundingRate } from "@qmi/contracts";
import type { Logger } from "@qmi/observability";
import { computeBackoffDelayMs, DEFAULT_BACKOFF } from "../reconnect.js";
import { PHASE1_SYMBOLS } from "../symbols.js";
import { BINANCE_EXCHANGE } from "./binance-parsers.js";
import { parseBasisMessage, parseFundingRateMessage } from "./binance-futures-parsers.js";

const STREAM_BASE_URL = "wss://fstream.binance.com/stream";
const MARK_PRICE_UPDATE_SPEED = "1s";

function buildStreamUrl(symbols: readonly { binance: string }[]): string {
  const streams = symbols.map((s) => `${s.binance}@markPrice@${MARK_PRICE_UPDATE_SPEED}`);
  return `${STREAM_BASE_URL}?streams=${streams.join("/")}`;
}

export interface BinanceFuturesAdapterOptions {
  logger: Logger;
  symbols?: readonly { canonical: string; binance: string }[];
  /** Injectable for tests; defaults to the global WebSocket client. */
  createSocket?: (url: string) => WebSocket;
}

/**
 * Binance USDT-M perpetual futures adapter: funding rate and futures-vs-index
 * basis only (brief Section 12; "options later" per the Phase 9 task list,
 * so no options data here). Public market-data streams only — no API key, no
 * order placement capability exists in this class.
 *
 * Deliberately not an `ExchangeAdapter` (../exchange-adapter.ts) — that
 * interface's trade/OHLCV/order-book shape is spot market data; forcing
 * funding-rate/basis into the same shape would be artificial. This is its
 * own small adapter with its own two event types.
 *
 * Open interest is not ingested: Binance doesn't push it over the public
 * WebSocket streams this service otherwise relies on (it's REST-poll only,
 * `GET /fapi/v1/openInterest`), and this service has no periodic-polling
 * mechanism yet — everything else it does is WebSocket-push. Adding a
 * fundamentally different ingestion pattern for one field is deferred until
 * a real consumer needs open interest specifically.
 */
export class BinanceFuturesAdapter {
  readonly exchangeName = BINANCE_EXCHANGE;

  private readonly logger: Logger;
  private readonly symbols: readonly { canonical: string; binance: string }[];
  private readonly createSocket: (url: string) => WebSocket;

  private socket: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private closedByCaller = false;

  private fundingRateHandlers: Array<(rate: FundingRate) => void> = [];
  private basisHandlers: Array<(basis: Basis) => void> = [];
  private errorHandlers: Array<(error: Error) => void> = [];

  constructor(options: BinanceFuturesAdapterOptions) {
    this.logger = options.logger;
    this.symbols = options.symbols ?? PHASE1_SYMBOLS;
    this.createSocket = options.createSocket ?? ((url) => new WebSocket(url));
  }

  onFundingRate(handler: (rate: FundingRate) => void): void {
    this.fundingRateHandlers.push(handler);
  }

  onBasis(handler: (basis: Basis) => void): void {
    this.basisHandlers.push(handler);
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
      this.logger.info({ exchange: this.exchangeName }, "futures market-data websocket connected");
    });

    socket.addEventListener("message", (event: MessageEvent) => {
      this.handleMessage(event.data);
    });

    socket.addEventListener("error", () => {
      this.emitError(new Error("websocket error"));
    });

    socket.addEventListener("close", () => {
      this.logger.warn({ exchange: this.exchangeName }, "futures market-data websocket closed");
      if (!this.closedByCaller) {
        this.scheduleReconnect();
      }
    });
  }

  private scheduleReconnect(): void {
    const delay = computeBackoffDelayMs(this.reconnectAttempt, DEFAULT_BACKOFF);
    this.reconnectAttempt += 1;
    this.logger.info(
      { exchange: this.exchangeName, delayMs: delay },
      "scheduling futures market-data reconnect",
    );
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
      if (stream.includes("@markPrice")) {
        const fundingRate = parseFundingRateMessage(data);
        this.fundingRateHandlers.forEach((h) => h(fundingRate));
        const basis = parseBasisMessage(data);
        this.basisHandlers.forEach((h) => h(basis));
      }
    } catch (error) {
      this.emitError(error instanceof Error ? error : new Error(String(error)));
    }
  }

  private emitError(error: Error): void {
    this.logger.warn(
      { exchange: this.exchangeName, error: error.message },
      "futures market-data adapter error",
    );
    this.errorHandlers.forEach((h) => h(error));
  }
}
