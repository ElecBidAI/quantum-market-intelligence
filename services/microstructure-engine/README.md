# microstructure-engine

Not implemented yet.

Order book / order flow / liquidity analytics (brief Section 5): spread, mid
price, microprice, depth, book imbalance, order-flow imbalance, slippage,
Amihud illiquidity, market-impact estimates. None of this is implemented —
Phase 2 only added OHLC-based volatility estimators (Parkinson, Garman-Klass,
Rogers-Satchell, ATR — `packages/quant-core/src/quant_core/volatility.py`),
which use closing-bar ranges, not the live order-book snapshots
`services/market-data` already ingests (`orderbook_snapshots` table). True
microstructure analytics are still Phase 6 work.

See [`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](../../docs/architecture/QMI-MASTER-ARCHITECTURE.md)
for how this service fits into the overall pipeline, and
[`docs/risk/RISK-GOVERNANCE.md`](../../docs/risk/RISK-GOVERNANCE.md) for the risk
rules it must obey once implemented.
