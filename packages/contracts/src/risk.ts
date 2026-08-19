import { z } from "zod";
import { isoTimestamp } from "./common.js";

/** Machine-readable risk reason (docs/risk/RISK-GOVERNANCE.md Section 2). */
export const riskReason = z.object({
  code: z.string().min(1),
  detail: z.string(),
});
export type RiskReason = z.infer<typeof riskReason>;

/**
 * Risk Engine decision (docs/architecture/DATA-CONTRACTS.md Section 7).
 *
 * sizingAdjustment is required when decision === "REDUCE" and must be null
 * otherwise, enforced by the refinement below.
 */
export const riskDecision = z
  .object({
    decision: z.enum(["APPROVE", "REDUCE", "REJECT"]),
    strategyId: z.string().min(1),
    reasons: z.array(riskReason),
    sizingAdjustment: z.number().positive().nullable(),
    timestamp: isoTimestamp,
  })
  .refine(
    (d) => (d.decision === "REDUCE" ? d.sizingAdjustment !== null : d.sizingAdjustment === null),
    {
      message: "sizingAdjustment must be set if and only if decision is REDUCE",
      path: ["sizingAdjustment"],
    },
  );
export type RiskDecision = z.infer<typeof riskDecision>;
