import { z } from "zod";
import { isoTimestamp } from "./common.js";

/**
 * Strategy candidate (docs/architecture/DATA-CONTRACTS.md Section 6).
 *
 * This is a CANDIDATE, never an executable order. It only becomes actionable
 * after riskDecision resolves it to APPROVE or REDUCE — see
 * docs/risk/RISK-GOVERNANCE.md Section 1.
 */
export const strategyCandidate = z.object({
  strategyId: z.string().min(1),
  symbol: z.string().min(1),
  venue: z.string().min(1),
  direction: z.enum(["LONG", "SHORT", "NEUTRAL"]),
  horizon: z.string().min(1),
  signalStrength: z.number(),
  entryLogic: z.record(z.unknown()),
  invalidationLogic: z.record(z.unknown()),
  stopLogic: z.record(z.unknown()),
  targetLogic: z.record(z.unknown()),
  expectedEdge: z.number(),
  estimatedCosts: z.number(),
  regime: z.string().min(1),
  timestamp: isoTimestamp,
});
export type StrategyCandidate = z.infer<typeof strategyCandidate>;
