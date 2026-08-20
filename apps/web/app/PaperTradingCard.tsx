"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { decisionLabel, directionLabel } from "../lib/i18n";
import { THEME } from "../lib/theme";
import { useLocale } from "./LocaleProvider";

interface PortfolioSnapshot {
  equity: number;
  realizedPnlTotal: number;
  unrealizedPnlTotal: number;
  grossExposurePct: number;
  netExposurePct: number;
  positions: Record<string, { netSize: number; avgEntryPrice: number }>;
  timestamp: string;
}

interface PaperOrderWithFill {
  orderId: string;
  strategyId: string;
  symbol: string;
  direction: "LONG" | "SHORT";
  sizePct: number;
  riskDecisionCode: "APPROVE" | "REDUCE";
  createdAt: string;
  fillPrice: number | null;
  fillTimestamp: string | null;
}

/**
 * Shows the latest simulated portfolio snapshot + recent paper orders
 * (`portfolio_snapshots`/`paper_orders`/`fills`, via GET
 * /paper-trading/latest) — the first time services/paper-execution runs
 * against the real regime->strategy->risk chain instead of only its own
 * test's synthetic fixtures. Simulated paper account only; nothing here
 * places a real order.
 */
export default function PaperTradingCard() {
  const { locale, t } = useLocale();
  const [snapshot, setSnapshot] = useState<PortfolioSnapshot | null>(null);
  const [recentOrders, setRecentOrders] = useState<PaperOrderWithFill[]>([]);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  useEffect(() => {
    let cancelled = false;

    apiFetch("/paper-trading/latest")
      .then((res) => {
        if (!res.ok) throw new Error(`unexpected status ${res.status}`);
        return res.json();
      })
      .then((body: { snapshot: PortfolioSnapshot | null; recentOrders: PaperOrderWithFill[] }) => {
        if (cancelled) return;
        setSnapshot(body.snapshot);
        setRecentOrders(body.recentOrders);
        setStatus("loaded");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const positions = snapshot ? Object.entries(snapshot.positions) : [];

  return (
    <section>
      <h2 style={headingStyle}>{t("paperTrading.heading")}</h2>
      <p style={framingStyle}>{t("paperTrading.framing")}</p>

      {status === "loading" && <p style={mutedStyle}>{t("paperTrading.loading")}</p>}
      {status === "error" && <p style={mutedStyle}>{t("paperTrading.error")}</p>}
      {status === "loaded" && !snapshot && <p style={mutedStyle}>{t("paperTrading.empty")}</p>}

      {snapshot && (
        <>
          <table style={{ borderCollapse: "collapse", fontSize: "0.9rem", marginBottom: "1rem" }}>
            <tbody>
              <tr>
                <td style={labelCellStyle}>{t("paperTrading.equityLabel")}</td>
                <td style={cellStyle}>{snapshot.equity.toFixed(2)}</td>
              </tr>
              <tr>
                <td style={labelCellStyle}>{t("paperTrading.realizedPnlLabel")}</td>
                <td style={cellStyle}>{snapshot.realizedPnlTotal.toFixed(4)}</td>
              </tr>
              <tr>
                <td style={labelCellStyle}>{t("paperTrading.unrealizedPnlLabel")}</td>
                <td style={cellStyle}>{snapshot.unrealizedPnlTotal.toFixed(4)}</td>
              </tr>
              <tr>
                <td style={labelCellStyle}>{t("paperTrading.grossExposureLabel")}</td>
                <td style={cellStyle}>{(snapshot.grossExposurePct * 100).toFixed(2)}%</td>
              </tr>
              <tr>
                <td style={labelCellStyle}>{t("paperTrading.netExposureLabel")}</td>
                <td style={cellStyle}>{(snapshot.netExposurePct * 100).toFixed(2)}%</td>
              </tr>
            </tbody>
          </table>

          <h3 style={subheadingStyle}>{t("paperTrading.positionsHeading")}</h3>
          {positions.length === 0 ? (
            <p style={mutedStyle}>{t("paperTrading.noPositions")}</p>
          ) : (
            <table style={{ borderCollapse: "collapse", width: "100%", marginBottom: "1rem" }}>
              <thead>
                <tr>
                  <th style={headerCellStyle}>{t("dashboard.colSymbol")}</th>
                  <th style={headerCellStyle}>{t("paperTrading.netSizeLabel")}</th>
                  <th style={headerCellStyle}>{t("paperTrading.avgEntryLabel")}</th>
                </tr>
              </thead>
              <tbody>
                {positions.map(([symbol, position]) => (
                  <tr key={symbol}>
                    <td style={cellStyle}>{symbol}</td>
                    <td style={cellStyle}>{(position.netSize * 100).toFixed(2)}%</td>
                    <td style={cellStyle}>{position.avgEntryPrice.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          <h3 style={subheadingStyle}>{t("paperTrading.recentOrdersHeading")}</h3>
          {recentOrders.length === 0 ? (
            <p style={mutedStyle}>{t("paperTrading.noOrders")}</p>
          ) : (
            <table style={{ borderCollapse: "collapse", width: "100%" }}>
              <thead>
                <tr>
                  <th style={headerCellStyle}>{t("dashboard.colSymbol")}</th>
                  <th style={headerCellStyle}>{t("signals.directionLabel")}</th>
                  <th style={headerCellStyle}>{t("signals.riskDecisionLabel")}</th>
                  <th style={headerCellStyle}>{t("paperTrading.netSizeLabel")}</th>
                  <th style={headerCellStyle}>{t("dashboard.colPrice")}</th>
                </tr>
              </thead>
              <tbody>
                {recentOrders.map((order) => (
                  <tr key={order.orderId}>
                    <td style={cellStyle}>{order.symbol}</td>
                    <td style={cellStyle}>{directionLabel(locale, order.direction)}</td>
                    <td style={cellStyle}>{decisionLabel(locale, order.riskDecisionCode)}</td>
                    <td style={cellStyle}>{(order.sizePct * 100).toFixed(2)}%</td>
                    <td style={cellStyle}>{order.fillPrice?.toFixed(2) ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}

const headingStyle: CSSProperties = { color: THEME.textPrimary, fontSize: "1.1rem", margin: "0 0 0.35rem" };

const framingStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const mutedStyle: CSSProperties = { color: THEME.textSecondary };

const cellStyle: CSSProperties = {
  borderBottom: `1px solid ${THEME.border}`,
  padding: "0.3rem 0.6rem",
  textAlign: "left",
  color: THEME.textPrimary,
  fontVariantNumeric: "tabular-nums",
};

const headerCellStyle: CSSProperties = {
  borderBottom: `1px solid ${THEME.border}`,
  padding: "0.3rem 0.6rem",
  textAlign: "left",
  color: THEME.textMuted,
  fontWeight: 400,
  fontSize: "0.85rem",
};

const labelCellStyle: CSSProperties = { padding: "0.15rem 0.5rem 0.15rem 0", textAlign: "left", color: THEME.textMuted };

const subheadingStyle: CSSProperties = {
  fontSize: "1rem",
  marginTop: "1rem",
  marginBottom: "0.5rem",
  color: THEME.textPrimary,
};
