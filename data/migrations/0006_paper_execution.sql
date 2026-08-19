-- QMI Phase 7 schema: paper orders, fills, and portfolio snapshots
-- (services/paper-execution). Written by
-- services/paper-execution/src/paper_execution/persistence.py.
--
-- No `positions` table: current positions are derived state (replay fills,
-- or read the latest portfolio_snapshots.positions JSONB), not
-- independently stored — storing them separately would be a second source
-- of truth that could drift from the fills ledger, which is exactly what
-- paper_execution.positions.reconcile() exists to catch if it ever happens
-- to an in-memory PositionBook. The DB layer avoids the problem instead of
-- needing to detect it.

CREATE TABLE IF NOT EXISTS paper_orders (
    order_id             TEXT PRIMARY KEY,
    strategy_id          TEXT NOT NULL,
    symbol               TEXT NOT NULL,
    direction            TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    size_pct             DOUBLE PRECISION NOT NULL,
    risk_decision_code   TEXT NOT NULL CHECK (risk_decision_code IN ('APPROVE', 'REDUCE')),
    created_at           TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_paper_orders_strategy ON paper_orders (strategy_id, created_at DESC);

CREATE TABLE IF NOT EXISTS fills (
    id                 BIGSERIAL PRIMARY KEY,
    order_id           TEXT NOT NULL REFERENCES paper_orders (order_id),
    symbol             TEXT NOT NULL,
    direction          TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT')),
    size_pct           DOUBLE PRECISION NOT NULL,
    price              DOUBLE PRECISION NOT NULL,
    "timestamp"        TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills (order_id);
CREATE INDEX IF NOT EXISTS idx_fills_symbol_time ON fills (symbol, "timestamp" DESC);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id                    BIGSERIAL PRIMARY KEY,
    equity                DOUBLE PRECISION NOT NULL,
    realized_pnl_total    DOUBLE PRECISION NOT NULL,
    unrealized_pnl_total  DOUBLE PRECISION NOT NULL,
    gross_exposure_pct    DOUBLE PRECISION NOT NULL,
    net_exposure_pct      DOUBLE PRECISION NOT NULL,
    positions             JSONB NOT NULL,
    "timestamp"           TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_time ON portfolio_snapshots ("timestamp" DESC);
