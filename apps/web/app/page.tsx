"use client";

import AuthGate from "./AuthGate";
import BrokerNarrativeCard from "./BrokerNarrativeCard";
import DerivativesCard from "./DerivativesCard";
import LanguageSwitcher from "./LanguageSwitcher";
import { useLocale } from "./LocaleProvider";
import MarketDashboard from "./MarketDashboard";
import PaperTradingCard from "./PaperTradingCard";
import SignalsCard from "./SignalsCard";

export default function HomePage() {
  const { t } = useLocale();

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: 720 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <h1>QMI — Phase 1</h1>
        <LanguageSwitcher />
      </div>
      <p>{t("page.description")}</p>
      <p>
        {t("page.docsIntro")} <code>docs/architecture/QMI-MASTER-ARCHITECTURE.md</code>{" "}
        {t("page.docsOutro")}
      </p>
      <AuthGate>
        <MarketDashboard />
        <DerivativesCard />
        <BrokerNarrativeCard />
        <SignalsCard />
        <PaperTradingCard />
      </AuthGate>
    </main>
  );
}
