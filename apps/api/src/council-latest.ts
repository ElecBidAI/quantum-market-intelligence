import type { QueryablePool } from "./db.js";

interface CouncilNarrativeDbRow {
  symbol: string;
  strategy_id: string | null;
  regime: string;
  regime_confidence: number;
  decision: "APPROVE" | "REDUCE" | "REJECT" | null;
  sizing_adjustment: number | null;
  final_stance: "SUPPORT" | "OPPOSE" | "NEUTRAL" | "VETO" | null;
  weighted_score: number | null;
  narrative: string;
  timestamp: string;
}

export interface CouncilNarrative {
  symbol: string;
  strategyId: string | null;
  regime: string;
  regimeConfidence: number;
  decision: "APPROVE" | "REDUCE" | "REJECT" | null;
  sizingAdjustment: number | null;
  finalStance: "SUPPORT" | "OPPOSE" | "NEUTRAL" | "VETO" | null;
  weightedScore: number | null;
  narrative: string;
  timestamp: string;
}

/**
 * Reads the most recent broker narrative per symbol
 * (data/migrations/0009_council_narratives.sql, written by
 * `python -m ai_council.run_narrative`). Read-only, same
 * one-query-per-symbol shape as `getLatestMarketState` — a symbol with no
 * narrative yet (the batch job hasn't run) simply isn't in the result, not
 * a fabricated placeholder row.
 */
export async function getLatestCouncilNarratives(
  pool: QueryablePool,
  symbols: readonly string[],
): Promise<CouncilNarrative[]> {
  const results: CouncilNarrative[] = [];
  for (const symbol of symbols) {
    const result = await pool.query<CouncilNarrativeDbRow>(
      `SELECT symbol, strategy_id, regime, regime_confidence, decision, sizing_adjustment,
              final_stance, weighted_score, narrative, "timestamp"
       FROM council_narratives
       WHERE symbol = $1
       ORDER BY "timestamp" DESC
       LIMIT 1`,
      [symbol],
    );
    const row = result.rows[0];
    if (!row) continue;
    results.push({
      symbol: row.symbol,
      strategyId: row.strategy_id,
      regime: row.regime,
      regimeConfidence: row.regime_confidence,
      decision: row.decision,
      sizingAdjustment: row.sizing_adjustment,
      finalStance: row.final_stance,
      weightedScore: row.weighted_score,
      narrative: row.narrative,
      timestamp: row.timestamp,
    });
  }
  return results;
}
