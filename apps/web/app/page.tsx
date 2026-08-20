"use client";

import { useState, type CSSProperties } from "react";
import AuthGate from "./AuthGate";
import BrokerNarrativeCard from "./BrokerNarrativeCard";
import DerivativesCard from "./DerivativesCard";
import LanguageSwitcher from "./LanguageSwitcher";
import { useLocale } from "./LocaleProvider";
import MarketDashboard from "./MarketDashboard";
import OrderBookPanel from "./OrderBookPanel";
import PaperTradingCard from "./PaperTradingCard";
import PriceChart from "./PriceChart";
import SignalsCard from "./SignalsCard";
import { THEME, FONT_FAMILY } from "../lib/theme";

const SYMBOLS = ["BTC-USDT", "ETH-USDT"] as const;

export default function HomePage() {
  const { t } = useLocale();
  const [activeSymbol, setActiveSymbol] = useState<string>(SYMBOLS[0]);

  return (
    <main style={mainStyle}>
      <header style={headerStyle}>
        <div>
          <h1 style={titleStyle}>QMI</h1>
          <p style={subtitleStyle}>{t("page.description")}</p>
        </div>
        <LanguageSwitcher />
      </header>

      <AuthGate>
        <div style={topGridStyle}>
          <div style={chartColumnStyle}>
            <div style={panelStyle}>
              <PriceChart symbol={activeSymbol} />
            </div>
          </div>
          <div style={sideColumnStyle}>
            <MarketDashboard activeSymbol={activeSymbol} onSelectSymbol={setActiveSymbol} />
            <OrderBookPanel symbol={activeSymbol} />
          </div>
        </div>

        <div style={cardsGridStyle}>
          <div style={panelStyle}>
            <BrokerNarrativeCard />
          </div>
          <div style={panelStyle}>
            <SignalsCard />
          </div>
          <div style={panelStyle}>
            <PaperTradingCard />
          </div>
          <div style={panelStyle}>
            <DerivativesCard />
          </div>
        </div>

        <p style={docsStyle}>
          {t("page.docsIntro")} <code>docs/architecture/QMI-MASTER-ARCHITECTURE.md</code>{" "}
          {t("page.docsOutro")}
        </p>
      </AuthGate>
    </main>
  );
}

const mainStyle: CSSProperties = {
  fontFamily: FONT_FAMILY,
  background: THEME.bg,
  minHeight: "100vh",
  padding: "1.25rem 1.5rem 3rem",
  color: THEME.textPrimary,
};

const headerStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: "1.25rem",
  gap: "1rem",
  flexWrap: "wrap",
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: "1.4rem",
  letterSpacing: "0.02em",
  color: THEME.accent,
};

const subtitleStyle: CSSProperties = { margin: "0.2rem 0 0", color: THEME.textSecondary, fontSize: "0.85rem" };

const topGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) 280px",
  gap: "1rem",
  marginBottom: "1.25rem",
};

const chartColumnStyle: CSSProperties = { minWidth: 0 };

const sideColumnStyle: CSSProperties = { display: "flex", flexDirection: "column", gap: "1rem" };

const panelStyle: CSSProperties = {
  background: THEME.panelBg,
  border: `1px solid ${THEME.border}`,
  borderRadius: 6,
  padding: "1rem",
};

const cardsGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
  gap: "1rem",
  marginBottom: "1.5rem",
};

const docsStyle: CSSProperties = { color: THEME.textMuted, fontSize: "0.8rem" };
