"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch, apiStreamUrl } from "../lib/api-client";
import {
  applyLatestSnapshot,
  applyOhlcvEvent,
  applyTickEvent,
  initMarketState,
  isLive,
  type MarketState,
} from "../lib/market-state";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

type ConnectionStatus = "connecting" | "connected" | "error";

export default function MarketDashboard() {
  const [state, setState] = useState<MarketState>(() => initMarketState(SYMBOLS));
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [now, setNow] = useState<Date>(new Date());

  useEffect(() => {
    const tick = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    let cancelled = false;

    apiFetch(`/market/latest?symbols=${SYMBOLS.join(",")}`)
      .then((res) => res.json())
      .then((body: { symbols: Parameters<typeof applyLatestSnapshot>[1] }) => {
        if (!cancelled) setState((prev) => applyLatestSnapshot(prev, body.symbols));
      })
      .catch(() => {
        // Initial snapshot is best-effort; the live stream below is the
        // source of truth once connected. We never substitute fake data.
      });

    const source = new EventSource(apiStreamUrl(`/stream/market?symbols=${SYMBOLS.join(",")}`));

    source.addEventListener("open", () => setStatus("connected"));
    source.addEventListener("error", () => setStatus("error"));
    source.addEventListener("tick", (event: MessageEvent<string>) => {
      const trade = JSON.parse(event.data) as Parameters<typeof applyTickEvent>[1];
      setState((prev) => applyTickEvent(prev, trade));
    });
    source.addEventListener("ohlcv", (event: MessageEvent<string>) => {
      const bar = JSON.parse(event.data) as Parameters<typeof applyOhlcvEvent>[1];
      setState((prev) => applyOhlcvEvent(prev, bar));
    });

    return () => {
      cancelled = true;
      source.close();
    };
  }, []);

  return (
    <section style={{ marginTop: "2rem" }}>
      <h2>Live prices</h2>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>
        Feed: /api (proxied) — connection {status}. Prices below are only ever what the
        exchange actually sent; a blank row means no data has arrived yet.
      </p>
      <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: 560 }}>
        <thead>
          <tr>
            <th style={cellStyle}>Symbol</th>
            <th style={cellStyle}>Exchange</th>
            <th style={cellStyle}>Last price</th>
            <th style={cellStyle}>Last update (UTC)</th>
            <th style={cellStyle}>Live</th>
          </tr>
        </thead>
        <tbody>
          {SYMBOLS.map((symbol) => {
            const row = state[symbol];
            const live = isLive(row?.lastUpdate ?? null, now);
            return (
              <tr key={symbol}>
                <td style={cellStyle}>{symbol}</td>
                <td style={cellStyle}>{row?.exchange ?? "—"}</td>
                <td style={cellStyle}>{row?.lastPrice ?? "—"}</td>
                <td style={cellStyle}>{row?.lastUpdate ?? "—"}</td>
                <td style={{ ...cellStyle, color: live ? "#0a7d32" : "#999" }}>
                  {live ? "LIVE" : "stale/no data"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </section>
  );
}

const cellStyle: CSSProperties = {
  border: "1px solid #ddd",
  padding: "0.4rem 0.6rem",
  textAlign: "left",
  fontVariantNumeric: "tabular-nums",
};
