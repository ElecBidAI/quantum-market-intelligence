import type { Ohlcv, OrderBookSnapshot, Trade } from "@qmi/contracts";

/**
 * Common interface every exchange adapter must implement
 * (docs/architecture/QMI-MASTER-ARCHITECTURE.md Section 5: "exchange
 * adapters live behind a common interface; no other service talks to an
 * exchange directly"). Phase 1 ships one implementation (BinanceAdapter).
 */
export interface ExchangeAdapter {
  readonly exchangeName: string;

  connect(): void;
  disconnect(): void;

  onTrade(handler: (trade: Trade) => void): void;
  onOhlcv(handler: (bar: Ohlcv) => void): void;
  onOrderBookSnapshot(handler: (snapshot: OrderBookSnapshot) => void): void;

  /** Fires with the raw error/reason whenever the connection drops or fails to parse a message. */
  onError(handler: (error: Error) => void): void;
}
