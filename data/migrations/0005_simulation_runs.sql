-- QMI Phase 5 schema: simulation runs (services/simulation-engine).
-- Written by services/simulation_engine/src/simulation_engine/persistence.py.

CREATE TABLE IF NOT EXISTS simulation_runs (
    id                 BIGSERIAL PRIMARY KEY,
    run_type           TEXT NOT NULL,          -- e.g. 'monte_carlo_trade_sequence', 'stress_test'
    strategy_id        TEXT,                    -- nullable: a simulation need not be tied to a strategy
    dataset_version    TEXT NOT NULL,
    parameters         JSONB NOT NULL,
    results            JSONB NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_simulation_runs_strategy ON simulation_runs (strategy_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_simulation_runs_type ON simulation_runs (run_type, created_at DESC);
