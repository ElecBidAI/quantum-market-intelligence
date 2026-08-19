import AuthGate from "./AuthGate";
import MarketDashboard from "./MarketDashboard";

export default function HomePage() {
  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: 720 }}>
      <h1>QMI — Phase 1</h1>
      <p>
        Live BTC/ETH spot prices from Binance only. No strategies, risk decisions, or
        execution capability exist yet.
      </p>
      <p>
        See <code>docs/architecture/QMI-MASTER-ARCHITECTURE.md</code> for the target
        architecture and development phases.
      </p>
      <AuthGate>
        <MarketDashboard />
      </AuthGate>
    </main>
  );
}
