import type { StrategyCandidate, RiskDecision } from "@qmi/contracts";
import type { QueryablePool } from "./db.js";

interface SignalDbRow {
  strategy_id: string;
  symbol: string;
  venue: string;
  direction: string;
  horizon: string;
  signal_strength: number;
  entry_logic: Record<string, unknown>;
  invalidation_logic: Record<string, unknown>;
  stop_logic: Record<string, unknown>;
  target_logic: Record<string, unknown>;
  expected_edge: number;
  estimated_costs: number;
  regime: string;
  timestamp: string;
}

interface RiskDecisionDbRow {
  decision: string;
  strategy_id: string;
  symbol: string;
  reasons: { code: string; detail: string }[];
  sizing_adjustment: number | null;
  timestamp: string;
}

export interface LatestSignal {
  symbol: string;
  candidate: StrategyCandidate;
  riskDecision: RiskDecision | null;
}

/**
 * Reads the most recent strategy candidate + its risk decision per symbol
 * (`signals`/`risk_decisions`, both from data/migrations/0001_init.sql,
 * written together by services/ai-council/src/ai_council/run_pipeline.py).
 * The two rows are correlated by `symbol` + `strategy_id` + an
 * exactly-matching `timestamp` — run_pipeline.py deliberately passes the
 * candidate's own timestamp into `risk_engine.evaluate(now=...)` so this
 * join is exact. `risk_decisions.symbol` was added specifically for this
 * (`data/migrations/0011_risk_decisions_symbol.sql`) after real-data
 * verification showed `strategy_id` + `timestamp` alone is ambiguous: two
 * different symbols can pick the same strategy in the same pipeline run
 * with bars sharing a last-bar timestamp (routine, since OHLCV bars are
 * minute-aligned), which silently returned the wrong symbol's decision. A
 * symbol with no signal yet is simply absent from the response; a signal
 * whose risk decision doesn't correlate (shouldn't happen given how
 * they're written) gets `riskDecision: null` rather than a fabricated
 * match.
 */
export async function getLatestSignals(
  pool: QueryablePool,
  symbols: readonly string[],
): Promise<LatestSignal[]> {
  const results: LatestSignal[] = [];
  for (const symbol of symbols) {
    const signalResult = await pool.query<SignalDbRow>(
      `SELECT strategy_id, symbol, venue, direction, horizon, signal_strength,
              entry_logic, invalidation_logic, stop_logic, target_logic,
              expected_edge, estimated_costs, regime, "timestamp"
       FROM signals
       WHERE symbol = $1
       ORDER BY "timestamp" DESC
       LIMIT 1`,
      [symbol],
    );
    const signalRow = signalResult.rows[0];
    if (!signalRow) continue;

    const decisionResult = await pool.query<RiskDecisionDbRow>(
      `SELECT decision, strategy_id, symbol, reasons, sizing_adjustment, "timestamp"
       FROM risk_decisions
       WHERE symbol = $1 AND strategy_id = $2 AND "timestamp" = $3
       ORDER BY created_at DESC
       LIMIT 1`,
      [symbol, signalRow.strategy_id, signalRow.timestamp],
    );
    const decisionRow = decisionResult.rows[0];

    results.push({
      symbol,
      candidate: {
        strategyId: signalRow.strategy_id,
        symbol: signalRow.symbol,
        venue: signalRow.venue,
        direction: signalRow.direction as StrategyCandidate["direction"],
        horizon: signalRow.horizon,
        signalStrength: signalRow.signal_strength,
        entryLogic: signalRow.entry_logic,
        invalidationLogic: signalRow.invalidation_logic,
        stopLogic: signalRow.stop_logic,
        targetLogic: signalRow.target_logic,
        expectedEdge: signalRow.expected_edge,
        estimatedCosts: signalRow.estimated_costs,
        regime: signalRow.regime,
        timestamp: signalRow.timestamp,
      },
      riskDecision: decisionRow
        ? {
            decision: decisionRow.decision as RiskDecision["decision"],
            strategyId: decisionRow.strategy_id,
            reasons: decisionRow.reasons,
            sizingAdjustment: decisionRow.sizing_adjustment,
            timestamp: decisionRow.timestamp,
          }
        : null,
    });
  }
  return results;
}
