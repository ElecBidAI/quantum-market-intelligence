-- QMI Phase 4 schema: backtest runs and reproducible research experiment
-- records (services/backtester). Written by
-- services/backtester/src/backtester/persistence.py.

CREATE TABLE IF NOT EXISTS backtests (
    id                 BIGSERIAL PRIMARY KEY,
    strategy_id        TEXT NOT NULL,
    symbol             TEXT NOT NULL,
    interval           TEXT NOT NULL,
    dataset_version    TEXT NOT NULL,
    parameters         JSONB NOT NULL,
    cost_assumptions   JSONB NOT NULL,
    metrics            JSONB NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_backtests_strategy_symbol ON backtests (strategy_id, symbol, created_at DESC);

-- Research Notebook / Audit Trail (brief Section 17): one row per
-- reproducible experiment, following the pipeline documented in
-- backtester/src/backtester/experiment.py.
CREATE TABLE IF NOT EXISTS research_runs (
    id                     BIGSERIAL PRIMARY KEY,
    hypothesis             TEXT NOT NULL,
    dataset_version        TEXT NOT NULL,
    transformations        JSONB NOT NULL,
    model_or_formula       TEXT NOT NULL,
    parameters             JSONB NOT NULL,
    cost_assumptions       JSONB NOT NULL,
    backtest_summary       JSONB NOT NULL,
    walk_forward_summary   JSONB,
    monte_carlo_summary    JSONB,
    stress_test_summary    JSONB,
    risk_review            JSONB,
    conclusion             TEXT NOT NULL,
    status                 TEXT NOT NULL CHECK (status IN ('REJECTED', 'RESEARCH', 'PAPER', 'APPROVED')),
    tags                   JSONB NOT NULL DEFAULT '[]'::JSONB,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_research_runs_status ON research_runs (status, created_at DESC);
