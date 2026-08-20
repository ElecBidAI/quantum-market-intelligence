"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { decisionLabel, regimeLabel, stanceLabel } from "../lib/i18n";
import { useLocale } from "./LocaleProvider";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

interface CouncilNarrative {
  symbol: string;
  strategyId: string | null;
  regime: string;
  regimeConfidence: number;
  decision: "APPROVE" | "REDUCE" | "REJECT" | null;
  finalStance: "SUPPORT" | "OPPOSE" | "NEUTRAL" | "VETO" | null;
  narrativeEn: string;
  narrativeEs: string;
  timestamp: string;
}

/**
 * Shows the latest deterministic broker narrative per symbol
 * (services/ai_council/narrator.py, via GET /council/narrative). This is
 * an explanation of a decision risk_engine and ai_council already made —
 * nothing here places, sizes, or executes a trade, and this component adds
 * no styling that could read as a buy/sell signal (plain text, no
 * bullish/bearish coloring).
 */
export default function BrokerNarrativeCard() {
  const { locale, t } = useLocale();
  const [narratives, setNarratives] = useState<CouncilNarrative[] | null>(null);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  useEffect(() => {
    let cancelled = false;

    apiFetch(`/council/narrative?symbols=${SYMBOLS.join(",")}`)
      .then((res) => {
        if (!res.ok) throw new Error(`unexpected status ${res.status}`);
        return res.json();
      })
      .then((body: { narratives: CouncilNarrative[] }) => {
        if (cancelled) return;
        setNarratives(body.narratives);
        setStatus("loaded");
      })
      .catch(() => {
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <section style={{ marginTop: "2rem" }}>
      <h2>{t("narrative.heading")}</h2>
      <p style={{ color: "#666", fontSize: "0.9rem" }}>{t("narrative.framing")}</p>

      {status === "loading" && <p>{t("narrative.loading")}</p>}
      {status === "error" && <p>{t("narrative.error")}</p>}
      {status === "loaded" && narratives?.length === 0 && (
        <p style={{ color: "#666" }}>{t("narrative.empty")}</p>
      )}

      {narratives?.map((item) => {
        const narrative = locale === "es" ? item.narrativeEs : item.narrativeEn;
        return (
          <article key={item.symbol} style={cardStyle}>
            <header style={{ marginBottom: "0.5rem" }}>
              <strong>{item.symbol}</strong>
              <span style={metaStyle}>
                {" "}
                — {t("narrative.regimeLabel")} {regimeLabel(locale, item.regime)} (
                {(item.regimeConfidence * 100).toFixed(0)}% {t("narrative.confidenceSuffix")})
                {item.strategyId ? `, ${t("narrative.strategyLabel")} ${item.strategyId}` : ""}
                {item.decision
                  ? `, ${t("narrative.decisionLabel")} ${decisionLabel(locale, item.decision)}`
                  : ""}
                {item.finalStance
                  ? `, ${t("narrative.councilLabel")} ${stanceLabel(locale, item.finalStance)}`
                  : ""}
              </span>
            </header>
            {narrative.split("\n\n").map((paragraph, i, all) => (
              <p key={i} style={i === all.length - 1 ? disclaimerStyle : paragraphStyle}>
                {paragraph}
              </p>
            ))}
            <p style={timestampStyle}>
              {t("narrative.generatedAtPrefix")} {item.timestamp} {t("narrative.generatedAtSuffix")}
            </p>
          </article>
        );
      })}
    </section>
  );
}

const cardStyle: CSSProperties = {
  border: "1px solid #ddd",
  borderRadius: 4,
  padding: "1rem",
  marginBottom: "1rem",
  maxWidth: 640,
};

const metaStyle: CSSProperties = { color: "#666", fontSize: "0.85rem" };

const paragraphStyle: CSSProperties = { fontSize: "0.95rem", lineHeight: 1.5 };

const disclaimerStyle: CSSProperties = {
  fontSize: "0.85rem",
  lineHeight: 1.5,
  fontStyle: "italic",
  color: "#555",
  borderTop: "1px solid #eee",
  paddingTop: "0.5rem",
  marginTop: "0.75rem",
};

const timestampStyle: CSSProperties = { color: "#999", fontSize: "0.8rem" };
