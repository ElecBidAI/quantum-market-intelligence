"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { THEME } from "../lib/theme";
import { useLocale } from "./LocaleProvider";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

// Below this many completed trades, every ratio in `metrics` is more noise
// than signal — shown anyway (never hidden), but flagged plainly.
const SMALL_SAMPLE_TRADE_THRESHOLD = 30;

interface BacktestMetrics {
  sampleSizeBars: number;
  numTrades: number;
  totalReturn: number;
  sharpeRatio: number | null;
  winRate: number | null;
  [key: string]: number | null;
}

interface Backtest {
  strategyId: string;
  symbol: string;
  interval: string;
  datasetVersion: string;
  metrics: BacktestMetrics;
  createdAt: string;
}

function formatRatio(value: number | null): string {
  return value === null ? "—" : value.toFixed(2);
}

function formatPercent(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(2)}%`;
}

/**
 * Shows the latest real backtest per (strategy, symbol) — GET
 * /research/backtests, written by `python -m backtester.research_runner`
 * against real ingested OHLCV history. Complements SignalsCard/
 * BrokerNarrativeCard: those explain the live pick, this shows whether
 * that strategy's own track record actually backs it up. A `null` metric
 * means mathematically undefined at the current sample size — rendered as
 * "—", never a fabricated zero.
 */
export default function StrategyResearchCard() {
  const { t } = useLocale();
  const [backtests, setBacktests] = useState<Backtest[] | null>(null);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  useEffect(() => {
    let cancelled = false;

    apiFetch(`/research/backtests?symbols=${SYMBOLS.join(",")}`)
      .then((res) => {
        if (!res.ok) throw new Error(`unexpected status ${res.status}`);
        return res.json();
      })
      .then((body: { backtests: Backtest[] }) => {
        if (cancelled) return;
        setBacktests(body.backtests);
        setStatus("loaded");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const bySymbol = new Map<string, Backtest[]>();
  for (const backtest of backtests ?? []) {
    const list = bySymbol.get(backtest.symbol) ?? [];
    list.push(backtest);
    bySymbol.set(backtest.symbol, list);
  }

  return (
    <section>
      <h2 style={headingStyle}>{t("research.heading")}</h2>
      <p style={framingStyle}>{t("research.framing")}</p>

      {status === "loading" && <p style={mutedStyle}>{t("research.loading")}</p>}
      {status === "error" && <p style={mutedStyle}>{t("research.error")}</p>}
      {status === "loaded" && bySymbol.size === 0 && <p style={mutedStyle}>{t("research.empty")}</p>}

      {[...bySymbol.entries()].map(([symbol, rows]) => (
        <div key={symbol} style={{ marginBottom: "1rem" }}>
          <strong style={{ color: THEME.textPrimary }}>{symbol}</strong>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.85rem", marginTop: "0.4rem" }}>
            <thead>
              <tr>
                <th style={headerCellStyle}>{t("research.strategyLabel")}</th>
                <th style={headerCellStyle}>{t("research.sharpeLabel")}</th>
                <th style={headerCellStyle}>{t("research.winRateLabel")}</th>
                <th style={headerCellStyle}>{t("research.totalReturnLabel")}</th>
                <th style={headerCellStyle}>{t("research.tradesLabel")}</th>
                <th style={headerCellStyle}>{t("research.sampleLabel")}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const smallSample = row.metrics.numTrades < SMALL_SAMPLE_TRADE_THRESHOLD;
                return (
                  <tr key={row.strategyId}>
                    <td style={cellStyle}>{row.strategyId}</td>
                    <td style={cellStyle}>{formatRatio(row.metrics.sharpeRatio)}</td>
                    <td style={cellStyle}>{formatPercent(row.metrics.winRate)}</td>
                    <td style={cellStyle}>{formatPercent(row.metrics.totalReturn)}</td>
                    <td style={cellStyle}>{row.metrics.numTrades}</td>
                    <td style={{ ...cellStyle, color: smallSample ? THEME.accent : THEME.textPrimary }}>
                      {row.metrics.sampleSizeBars}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {rows.some((row) => row.metrics.numTrades < SMALL_SAMPLE_TRADE_THRESHOLD) && (
            <p style={warningStyle}>{t("research.smallSampleWarning")}</p>
          )}
        </div>
      ))}
    </section>
  );
}

const headingStyle: CSSProperties = { color: THEME.textPrimary, fontSize: "1.1rem", margin: "0 0 0.35rem" };

const framingStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const mutedStyle: CSSProperties = { color: THEME.textSecondary };

const headerCellStyle: CSSProperties = {
  borderBottom: `1px solid ${THEME.border}`,
  padding: "0.3rem 0.5rem",
  textAlign: "left",
  color: THEME.textMuted,
  fontWeight: 400,
  fontSize: "0.8rem",
};

const cellStyle: CSSProperties = {
  borderBottom: `1px solid ${THEME.border}`,
  padding: "0.3rem 0.5rem",
  textAlign: "left",
  color: THEME.textPrimary,
  fontVariantNumeric: "tabular-nums",
};

const warningStyle: CSSProperties = {
  color: THEME.accent,
  fontSize: "0.75rem",
  marginTop: "0.3rem",
};
