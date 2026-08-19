/**
 * Phase 1 universe: BTC and ETH only (brief Section 1 lists these as the
 * required starting pair; the remaining ~20 liquid assets are added once
 * this adapter has proven itself, not all at once).
 */
export interface SymbolMapping {
  /** Canonical QMI symbol, e.g. "BTC-USDT" (docs/architecture/DATA-CONTRACTS.md). */
  canonical: string;
  /** Binance's wire symbol, e.g. "btcusdt" (lowercase, no separator). */
  binance: string;
}

export const PHASE1_SYMBOLS: readonly SymbolMapping[] = [
  { canonical: "BTC-USDT", binance: "btcusdt" },
  { canonical: "ETH-USDT", binance: "ethusdt" },
];

const byBinanceSymbol = new Map(PHASE1_SYMBOLS.map((s) => [s.binance, s.canonical]));

/** Resolves a Binance wire symbol (any case) to its canonical QMI symbol. */
export function toCanonicalSymbol(binanceSymbol: string): string | undefined {
  return byBinanceSymbol.get(binanceSymbol.toLowerCase());
}
