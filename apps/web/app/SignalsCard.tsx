"use client";

import { useEffect, useState, type CSSProperties } from "react";
import { apiFetch } from "../lib/api-client";
import { decisionLabel, directionLabel, regimeLabel } from "../lib/i18n";
import { THEME } from "../lib/theme";
import { useLocale } from "./LocaleProvider";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

interface StrategyCandidate {
  strategyId: string;
  symbol: string;
  direction: "LONG" | "SHORT" | "NEUTRAL";
  horizon: string;
  signalStrength: number;
  entryLogic: Record<string, unknown>;
  stopLogic: Record<string, unknown>;
  targetLogic: Record<string, unknown>;
  expectedEdge: number;
  estimatedCosts: number;
  regime: string;
  timestamp: string;
}

interface RiskDecision {
  decision: "APPROVE" | "REDUCE" | "REJECT";
  reasons: { code: string; detail: string }[];
  sizingAdjustment: number | null;
}

interface LatestSignal {
  symbol: string;
  candidate: StrategyCandidate;
  riskDecision: RiskDecision | null;
}

function logicPrice(logic: Record<string, unknown>, key: string): number | undefined {
  const value = logic[key];
  return typeof value === "number" ? value : undefined;
}

/**
 * Shows the latest structured strategy candidate + risk decision per
 * symbol (`signals`/`risk_decisions`, via GET /signals/latest) —
 * complements BrokerNarrativeCard's prose with the raw structured data it
 * was generated from.
 */
export default function SignalsCard() {
  const { locale, t } = useLocale();
  const [signals, setSignals] = useState<LatestSignal[] | null>(null);
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");

  useEffect(() => {
    let cancelled = false;

    apiFetch(`/signals/latest?symbols=${SYMBOLS.join(",")}`)
      .then((res) => {
        if (!res.ok) throw new Error(`unexpected status ${res.status}`);
        return res.json();
      })
      .then((body: { signals: LatestSignal[] }) => {
        if (cancelled) return;
        setSignals(body.signals);
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
    <section>
      <h2 style={headingStyle}>{t("signals.heading")}</h2>
      <p style={framingStyle}>{t("signals.framing")}</p>

      {status === "loading" && <p style={mutedStyle}>{t("signals.loading")}</p>}
      {status === "error" && <p style={mutedStyle}>{t("signals.error")}</p>}
      {status === "loaded" && signals?.length === 0 && (
        <p style={mutedStyle}>{t("signals.empty")}</p>
      )}

      {signals?.map((item) => {
        const entry = logicPrice(item.candidate.entryLogic, "entryPrice");
        const stop = logicPrice(item.candidate.stopLogic, "stopPrice");
        const target = logicPrice(item.candidate.targetLogic, "targetPrice");
        return (
          <article key={item.symbol} style={cardStyle}>
            <header style={{ marginBottom: "0.5rem" }}>
              <strong>{item.symbol}</strong>
              <span style={metaStyle}>
                {" "}
                — {t("signals.strategyLabel")} {item.candidate.strategyId}, {t("signals.directionLabel")}{" "}
                {directionLabel(locale, item.candidate.direction)}, {regimeLabel(locale, item.candidate.regime)}
              </span>
            </header>
            <table style={{ borderCollapse: "collapse", fontSize: "0.9rem" }}>
              <tbody>
                <tr>
                  <td style={labelCellStyle}>{t("signals.horizonLabel")}</td>
                  <td style={cellStyle}>{item.candidate.horizon}</td>
                </tr>
                <tr>
                  <td style={labelCellStyle}>{t("signals.expectedEdgeLabel")}</td>
                  <td style={cellStyle}>{item.candidate.expectedEdge.toFixed(4)}</td>
                </tr>
                <tr>
                  <td style={labelCellStyle}>{t("signals.estimatedCostsLabel")}</td>
                  <td style={cellStyle}>{item.candidate.estimatedCosts.toFixed(4)}</td>
                </tr>
                {entry !== undefined && (
                  <tr>
                    <td style={labelCellStyle}>{t("signals.entryLabel")}</td>
                    <td style={cellStyle}>{entry}</td>
                  </tr>
                )}
                {stop !== undefined && (
                  <tr>
                    <td style={labelCellStyle}>{t("signals.stopLabel")}</td>
                    <td style={cellStyle}>{stop}</td>
                  </tr>
                )}
                {target !== undefined && (
                  <tr>
                    <td style={labelCellStyle}>{t("signals.targetLabel")}</td>
                    <td style={cellStyle}>{target}</td>
                  </tr>
                )}
                <tr>
                  <td style={labelCellStyle}>{t("signals.riskDecisionLabel")}</td>
                  <td style={cellStyle}>
                    {item.riskDecision
                      ? decisionLabel(locale, item.riskDecision.decision)
                      : t("signals.noRiskDecision")}
                  </td>
                </tr>
                {item.riskDecision && item.riskDecision.reasons.length > 0 && (
                  <tr>
                    <td style={labelCellStyle}>{t("signals.reasonsLabel")}</td>
                    <td style={cellStyle}>
                      {item.riskDecision.reasons.map((r) => r.detail).join("; ")}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </article>
        );
      })}
    </section>
  );
}

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

const cellStyle: CSSProperties = {
  padding: "0.15rem 0.5rem 0.15rem 0",
  textAlign: "left",
  color: THEME.textPrimary,
};

const labelCellStyle: CSSProperties = { ...cellStyle, color: THEME.textMuted };
