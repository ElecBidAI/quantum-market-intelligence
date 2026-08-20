"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { decisionLabel, regimeLabel, stanceLabel } from "../lib/i18n";
import { THEME } from "../lib/theme";
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
    <section style={sectionStyle}>
      <h2 style={headingStyle}>{t("narrative.heading")}</h2>
      <p style={framingStyle}>{t("narrative.framing")}</p>

      {status === "loading" && <p style={mutedStyle}>{t("narrative.loading")}</p>}
      {status === "error" && <p style={mutedStyle}>{t("narrative.error")}</p>}
      {status === "loaded" && narratives?.length === 0 && (
        <p style={mutedStyle}>{t("narrative.empty")}</p>
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

const sectionStyle: CSSProperties = { marginTop: 0 };

const headingStyle: CSSProperties = { color: THEME.textPrimary, fontSize: "1.1rem", margin: "0 0 0.35rem" };

const framingStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const mutedStyle: CSSProperties = { color: THEME.textSecondary };

const cardStyle: CSSProperties = {
  background: THEME.panelBg,
  border: `1px solid ${THEME.border}`,
  borderRadius: 6,
  padding: "1rem",
  marginBottom: "1rem",
};

const metaStyle: CSSProperties = { color: THEME.textSecondary, fontSize: "0.85rem" };

const paragraphStyle: CSSProperties = { fontSize: "0.95rem", lineHeight: 1.5, color: THEME.textPrimary };

const disclaimerStyle: CSSProperties = {
  fontSize: "0.85rem",
  lineHeight: 1.5,
  fontStyle: "italic",
  color: THEME.textMuted,
  borderTop: `1px solid ${THEME.border}`,
  paddingTop: "0.5rem",
  marginTop: "0.75rem",
};

const timestampStyle: CSSProperties = { color: THEME.textMuted, fontSize: "0.8rem" };
