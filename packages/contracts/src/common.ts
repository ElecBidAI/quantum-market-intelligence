import { z } from "zod";

/**
 * ISO 8601 timestamp string. QMI stores and passes timestamps as UTC ISO
 * strings everywhere (docs/architecture/DATA-CONTRACTS.md Section 1).
 */
export const isoTimestamp = z.string().datetime({ offset: true });

export const qualityStatus = z.enum(["ok", "suspect", "rejected"]);
export type QualityStatus = z.infer<typeof qualityStatus>;

/**
 * Provenance fields required on every ingested market/derivatives/context
 * record (docs/architecture/DATA-CONTRACTS.md Section 2).
 */
export const envelope = z.object({
  source: z.string().min(1),
  exchange: z.string().min(1),
  symbol: z.string().min(1),
  timestamp: isoTimestamp,
  ingestedAt: isoTimestamp,
  qualityStatus,
  schemaVersion: z.number().int().positive(),
});
export type Envelope = z.infer<typeof envelope>;
