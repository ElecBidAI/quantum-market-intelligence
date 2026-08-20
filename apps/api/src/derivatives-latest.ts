import type { QueryablePool } from "./db.js";

interface FundingRateDbRow {
  rate: number;
  interval_hours: number;
  timestamp: string;
}

interface BasisDbRow {
  spot_price: number;
  futures_price: number;
  basis: number;
  annualized_basis: number;
  timestamp: string;
}

export interface LatestDerivatives {
  symbol: string;
  fundingRate: { rate: number; intervalHours: number; timestamp: string } | null;
  basis: {
    spotPrice: number;
    futuresPrice: number;
    basis: number;
    annualizedBasis: number;
    timestamp: string;
  } | null;
}

/**
 * Reads the most recent funding rate and futures-vs-index basis per symbol
 * (data/migrations/0007_derivatives.sql, written by
 * services/market-data's BinanceFuturesAdapter). Same two-query-per-symbol
 * shape as `getLatestMarketState` (trade + bar) — a symbol with no
 * derivatives data yet gets `null` fields, never a fabricated value.
 */
export async function getLatestDerivatives(
  pool: QueryablePool,
  symbols: readonly string[],
): Promise<LatestDerivatives[]> {
  const results: LatestDerivatives[] = [];
  for (const symbol of symbols) {
    const fundingResult = await pool.query<FundingRateDbRow>(
      `SELECT rate, interval_hours, "timestamp"
       FROM funding_rates
       WHERE symbol = $1 AND quality_status <> 'rejected'
       ORDER BY "timestamp" DESC
       LIMIT 1`,
      [symbol],
    );
    const basisResult = await pool.query<BasisDbRow>(
      `SELECT spot_price, futures_price, basis, annualized_basis, "timestamp"
       FROM futures_basis
       WHERE symbol = $1 AND quality_status <> 'rejected'
       ORDER BY "timestamp" DESC
       LIMIT 1`,
      [symbol],
    );
    const fundingRow = fundingResult.rows[0];
    const basisRow = basisResult.rows[0];
    results.push({
      symbol,
      fundingRate: fundingRow
        ? { rate: fundingRow.rate, intervalHours: fundingRow.interval_hours, timestamp: fundingRow.timestamp }
        : null,
      basis: basisRow
        ? {
            spotPrice: basisRow.spot_price,
            futuresPrice: basisRow.futures_price,
            basis: basisRow.basis,
            annualizedBasis: basisRow.annualized_basis,
            timestamp: basisRow.timestamp,
          }
        : null,
    });
  }
  return results;
}
