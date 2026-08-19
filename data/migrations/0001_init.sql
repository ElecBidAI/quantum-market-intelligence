-- QMI Phase 0 initial schema.
--
-- Only the tables that already have a corresponding contract in
-- packages/contracts are created here (see docs/architecture/DATA-CONTRACTS.md
-- Section 9). The remaining tables in the target domain list are added in the
-- phase that first reads/writes them, so schema and code land together.
--
-- All timestamps are stored as TIMESTAMPTZ and must be written in UTC.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Strategy candidates proposed by strategy-engine (or any future producer).
-- A row here is never an executable order (see docs/risk/RISK-GOVERNANCE.md).
CREATE TABLE IF NOT EXISTS signals (
    id                  BIGSERIAL PRIMARY KEY,
    strategy_id         TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    venue               TEXT NOT NULL,
    direction           TEXT NOT NULL CHECK (direction IN ('LONG', 'SHORT', 'NEUTRAL')),
    horizon             TEXT NOT NULL,
    signal_strength     DOUBLE PRECISION NOT NULL,
    entry_logic         JSONB NOT NULL DEFAULT '{}'::JSONB,
    invalidation_logic  JSONB NOT NULL DEFAULT '{}'::JSONB,
    stop_logic          JSONB NOT NULL DEFAULT '{}'::JSONB,
    target_logic        JSONB NOT NULL DEFAULT '{}'::JSONB,
    expected_edge       DOUBLE PRECISION NOT NULL,
    estimated_costs     DOUBLE PRECISION NOT NULL,
    regime              TEXT NOT NULL,
    "timestamp"         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals (symbol, "timestamp" DESC);
CREATE INDEX IF NOT EXISTS idx_signals_strategy_id ON signals (strategy_id);

-- Risk Engine decisions. Immutable/append-only: corrections are new rows that
-- reference the original via strategy_id + timestamp, never UPDATEs.
CREATE TABLE IF NOT EXISTS risk_decisions (
    id                  BIGSERIAL PRIMARY KEY,
    decision            TEXT NOT NULL CHECK (decision IN ('APPROVE', 'REDUCE', 'REJECT')),
    strategy_id         TEXT NOT NULL,
    reasons             JSONB NOT NULL DEFAULT '[]'::JSONB,
    sizing_adjustment   DOUBLE PRECISION,
    "timestamp"         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_risk_decisions_strategy_id ON risk_decisions (strategy_id, "timestamp" DESC);

-- Append-only audit trail for governance-relevant events across the system.
CREATE TABLE IF NOT EXISTS audit_events (
    id                  BIGSERIAL PRIMARY KEY,
    event_type          TEXT NOT NULL,
    actor               TEXT NOT NULL,
    payload             JSONB NOT NULL DEFAULT '{}'::JSONB,
    "timestamp"         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_type_timestamp ON audit_events (event_type, "timestamp" DESC);

-- risk_decisions and audit_events are append-only by policy. No DELETE/UPDATE
-- privileges are granted to application roles beyond INSERT/SELECT; enforcing
-- this at the role/grant level is deferred to the phase that introduces
-- per-service database roles.
