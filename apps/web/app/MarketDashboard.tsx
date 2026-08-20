"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch, apiStreamUrl } from "../lib/api-client";
import { statusLabel } from "../lib/i18n";
import { THEME } from "../lib/theme";
import {
  applyLatestSnapshot,
  applyOhlcvEvent,
  applyTickEvent,
  initMarketState,
  isLive,
  type MarketState,
} from "../lib/market-state";
import { useLocale } from "./LocaleProvider";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

type ConnectionStatus = "connecting" | "connected" | "error";

/**
 * Compact watchlist: real last price + live/stale status per symbol,
 * clickable to switch PriceChart's active symbol. Was originally the
 * dashboard's primary (table) price view; PriceChart now owns that role,
 * so this shrank to a ticker strip — same fetch/SSE logic, smaller JSX.
 */
export default function MarketDashboard({
  activeSymbol,
  onSelectSymbol,
}: {
  activeSymbol: string;
  onSelectSymbol: (symbol: string) => void;
}) {
  const { locale, t } = useLocale();
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
    <section style={panelStyle}>
      <div style={headerRowStyle}>
        <h3 style={headingStyle}>{t("watchlist.heading")}</h3>
        <span style={statusDotStyle(status)} title={statusLabel(locale, status)} />
      </div>
      {SYMBOLS.map((symbol) => {
        const row = state[symbol];
        const live = isLive(row?.lastUpdate ?? null, now);
        const active = symbol === activeSymbol;
        return (
          <button
            key={symbol}
            type="button"
            onClick={() => onSelectSymbol(symbol)}
            style={rowStyle(active)}
          >
            <span style={{ color: THEME.textPrimary, fontWeight: 600 }}>{symbol}</span>
            <span style={{ ...priceStyle, color: live ? THEME.textPrimary : THEME.textMuted }}>
              {row?.lastPrice ?? "—"}
            </span>
          </button>
        );
      })}
    </section>
  );
}

const panelStyle: CSSProperties = {
  background: THEME.panelBg,
  border: `1px solid ${THEME.border}`,
  borderRadius: 6,
  padding: "0.75rem",
};

const headerRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  marginBottom: "0.5rem",
};

const headingStyle: CSSProperties = { margin: 0, fontSize: "0.9rem", color: THEME.textPrimary };

function statusDotStyle(status: ConnectionStatus): CSSProperties {
  const color = status === "connected" ? THEME.positive : status === "error" ? THEME.negative : THEME.textMuted;
  return { width: 8, height: 8, borderRadius: "50%", background: color, display: "inline-block" };
}

function rowStyle(active: boolean): CSSProperties {
  return {
    display: "flex",
    width: "100%",
    justifyContent: "space-between",
    alignItems: "center",
    background: active ? THEME.panelBgAlt : "transparent",
    border: "none",
    borderRadius: 4,
    padding: "0.4rem 0.5rem",
    marginBottom: "0.2rem",
    cursor: "pointer",
    textAlign: "left",
  };
}

const priceStyle: CSSProperties = { fontVariantNumeric: "tabular-nums", fontSize: "0.9rem" };
