"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { THEME } from "../lib/theme";
import { useLocale } from "./LocaleProvider";

interface OrderBookResponse {
  orderBook: {
    symbol: string;
    bids: [number, number][];
    asks: [number, number][];
    sequenceId: number;
    timestamp: string;
  } | null;
}

const DEPTH_ROWS = 10;
const POLL_INTERVAL_MS = 2000;

function formatSize(size: number): string {
  return size.toFixed(4);
}

/**
 * Real top-of-book depth ladder from GET /market/orderbook
 * (orderbook_snapshots, ingested by services/market-data's
 * `@depth20@100ms` Binance stream). Polled rather than pushed over SSE —
 * the stream only relays ticks/bars today, not book snapshots — so this
 * is honestly a few seconds behind, not tick-by-tick.
 */
export default function OrderBookPanel({ symbol }: { symbol: string }) {
  const { t } = useLocale();
  const [book, setBook] = useState<OrderBookResponse["orderBook"]>(null);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");

    function load(): void {
      apiFetch(`/market/orderbook?symbol=${symbol}`)
        .then((res) => {
          if (!res.ok) throw new Error(`unexpected status ${res.status}`);
          return res.json();
        })
        .then((body: OrderBookResponse) => {
          if (cancelled) return;
          setBook(body.orderBook);
          setStatus("loaded");
        })
        .catch(() => {
          if (!cancelled) setStatus("error");
        });
    }

    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [symbol]);

  const asks = book ? [...book.asks].sort((a, b) => a[0] - b[0]).slice(0, DEPTH_ROWS).reverse() : [];
  const bids = book ? [...book.bids].sort((a, b) => b[0] - a[0]).slice(0, DEPTH_ROWS) : [];
  const bestAsk = book && book.asks.length > 0 ? Math.min(...book.asks.map((a) => a[0])) : undefined;
  const bestBid = book && book.bids.length > 0 ? Math.max(...book.bids.map((b) => b[0])) : undefined;
  const spread = bestAsk !== undefined && bestBid !== undefined ? bestAsk - bestBid : undefined;

  return (
    <section style={panelStyle}>
      <h3 style={headingStyle}>
        {t("orderbook.heading")} — {symbol}
      </h3>

      {status === "loading" && <p style={mutedStyle}>{t("orderbook.loading")}</p>}
      {status === "error" && <p style={mutedStyle}>{t("orderbook.error")}</p>}
      {status === "loaded" && !book && <p style={mutedStyle}>{t("orderbook.empty")}</p>}

      {book && (
        <>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <thead>
              <tr>
                <th style={colHeaderStyle}>{t("orderbook.priceCol")}</th>
                <th style={{ ...colHeaderStyle, textAlign: "right" }}>{t("orderbook.sizeCol")}</th>
              </tr>
            </thead>
            <tbody>
              {asks.map(([price, size]) => (
                <tr key={`ask-${price}`}>
                  <td style={{ ...cellStyle, color: THEME.negative }}>{price}</td>
                  <td style={{ ...cellStyle, textAlign: "right" }}>{formatSize(size)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={spreadRowStyle}>
            {t("orderbook.spreadLabel")}: {spread !== undefined ? spread.toFixed(2) : "—"}
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8rem" }}>
            <tbody>
              {bids.map(([price, size]) => (
                <tr key={`bid-${price}`}>
                  <td style={{ ...cellStyle, color: THEME.positive }}>{price}</td>
                  <td style={{ ...cellStyle, textAlign: "right" }}>{formatSize(size)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}

const panelStyle: CSSProperties = {
  background: THEME.panelBg,
  border: `1px solid ${THEME.border}`,
  borderRadius: 6,
  padding: "0.75rem 1rem",
  color: THEME.textPrimary,
};

const headingStyle: CSSProperties = { margin: "0 0 0.5rem", fontSize: "0.95rem", color: THEME.textPrimary };

const mutedStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const colHeaderStyle: CSSProperties = {
  textAlign: "left",
  color: THEME.textMuted,
  fontWeight: 400,
  padding: "0.15rem 0",
  borderBottom: `1px solid ${THEME.border}`,
};

const cellStyle: CSSProperties = {
  padding: "0.1rem 0",
  fontVariantNumeric: "tabular-nums",
};

const spreadRowStyle: CSSProperties = {
  textAlign: "center",
  color: THEME.textSecondary,
  fontSize: "0.75rem",
  padding: "0.35rem 0",
  borderTop: `1px solid ${THEME.border}`,
  borderBottom: `1px solid ${THEME.border}`,
  margin: "0.25rem 0",
};
