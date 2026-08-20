"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { THEME } from "../lib/theme";
import { useLocale } from "./LocaleProvider";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

interface LatestDerivatives {
  symbol: string;
  fundingRate: { rate: number; intervalHours: number; timestamp: string } | null;
  basis: {
    spotPrice: number;
    futuresPrice: number;
    basis: number;
    annualizedBasis: number;
    timestamp: string;
  } | null;
}

/**
 * Shows the latest funding rate + futures-vs-index basis per symbol
 * (services/market-data's BinanceFuturesAdapter, via GET
 * /derivatives/latest). Plain numbers only — no bullish/bearish coloring
 * that could read as a trading signal, same restraint as MarketDashboard.
 */
export default function DerivativesCard() {
  const { t } = useLocale();
  const [derivatives, setDerivatives] = useState<LatestDerivatives[] | null>(null);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  useEffect(() => {
    let cancelled = false;

    apiFetch(`/derivatives/latest?symbols=${SYMBOLS.join(",")}`)
      .then((res) => {
        if (!res.ok) throw new Error(`unexpected status ${res.status}`);
        return res.json();
      })
      .then((body: { derivatives: LatestDerivatives[] }) => {
        if (cancelled) return;
        setDerivatives(body.derivatives);
        setStatus("loaded");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const hasAnyData = derivatives?.some((d) => d.fundingRate || d.basis) ?? false;

  return (
    <section>
      <h2 style={headingStyle}>{t("derivatives.heading")}</h2>
      <p style={framingStyle}>{t("derivatives.framing")}</p>

      {status === "loading" && <p style={mutedStyle}>{t("derivatives.loading")}</p>}
      {status === "error" && <p style={mutedStyle}>{t("derivatives.error")}</p>}
      {status === "loaded" && !hasAnyData && <p style={mutedStyle}>{t("derivatives.empty")}</p>}

      {status === "loaded" && hasAnyData && (
        <table style={{ borderCollapse: "collapse", width: "100%" }}>
          <thead>
            <tr>
              <th style={headerCellStyle}>{t("dashboard.colSymbol")}</th>
              <th style={headerCellStyle}>{t("derivatives.fundingRateLabel")}</th>
              <th style={headerCellStyle}>{t("derivatives.basisLabel")}</th>
            </tr>
          </thead>
          <tbody>
            {derivatives?.map((item) => (
              <tr key={item.symbol}>
                <td style={cellStyle}>{item.symbol}</td>
                <td style={cellStyle}>
                  {item.fundingRate
                    ? `${(item.fundingRate.rate * 100).toFixed(4)}% / ${item.fundingRate.intervalHours}${t("derivatives.everyHoursSuffix")}`
                    : t("derivatives.noFundingRate")}
                </td>
                <td style={cellStyle}>
                  {item.basis
                    ? `${item.basis.basis.toFixed(2)} (${(item.basis.annualizedBasis * 100).toFixed(2)}%)`
                    : t("derivatives.noBasis")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

const headingStyle: CSSProperties = { color: THEME.textPrimary, fontSize: "1.1rem", margin: "0 0 0.35rem" };

const framingStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const mutedStyle: CSSProperties = { color: THEME.textSecondary };

const headerCellStyle: CSSProperties = {
  borderBottom: `1px solid ${THEME.border}`,
  padding: "0.4rem 0.6rem",
  textAlign: "left",
  color: THEME.textMuted,
  fontWeight: 400,
  fontSize: "0.85rem",
};

const cellStyle: CSSProperties = {
  borderBottom: `1px solid ${THEME.border}`,
  padding: "0.4rem 0.6rem",
  textAlign: "left",
  color: THEME.textPrimary,
  fontVariantNumeric: "tabular-nums",
};
