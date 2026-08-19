export interface BackoffOptions {
  baseDelayMs: number;
  maxDelayMs: number;
}

export const DEFAULT_BACKOFF: BackoffOptions = {
  baseDelayMs: 1_000,
  maxDelayMs: 30_000,
};

/**
 * Exponential backoff delay for reconnect attempt `attempt` (0-indexed).
 * Deliberately deterministic (no jitter) so it stays trivially unit
 * testable; jitter can be layered on by the caller if thundering-herd
 * reconnects become an observed problem with more than one instance.
 */
export function computeBackoffDelayMs(attempt: number, options: BackoffOptions = DEFAULT_BACKOFF): number {
  if (attempt < 0) {
    throw new RangeError("attempt must be >= 0");
  }
  const delay = options.baseDelayMs * 2 ** attempt;
  return Math.min(delay, options.maxDelayMs);
}
