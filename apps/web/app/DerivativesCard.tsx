"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
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
    <section style={{ marginTop: "2rem" }}>
      <h2>{t("derivatives.heading")}</h2>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>{t("derivatives.framing")}</p>

      {status === "loading" && <p>{t("derivatives.loading")}</p>}
      {status === "error" && <p>{t("derivatives.error")}</p>}
      {status === "loaded" && !hasAnyData && <p style={{ color: "#666" }}>{t("derivatives.empty")}</p>}

      {status === "loaded" && hasAnyData && (
        <table style={{ borderCollapse: "collapse", width: "100%", maxWidth: 560 }}>
          <thead>
            <tr>
              <th style={cellStyle}>{t("dashboard.colSymbol")}</th>
              <th style={cellStyle}>{t("derivatives.fundingRateLabel")}</th>
              <th style={cellStyle}>{t("derivatives.basisLabel")}</th>
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

const cellStyle: CSSProperties = {
  border: "1px solid #ddd",
  padding: "0.4rem 0.6rem",
  textAlign: "left",
  fontVariantNumeric: "tabular-nums",
};
