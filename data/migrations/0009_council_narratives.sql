-- QMI broker-narrative persistence (services/ai-council/src/ai_council/narrator.py).
--
-- Append-only, same policy as risk_decisions (0001_init.sql): corrections
-- are new rows, never UPDATEs. No TS zod contract mirrors this table —
-- apps/api/src/council-latest.ts shapes its own response type inline, the
-- same way market-latest.ts does for LatestMarketState.
--
-- strategy_id, decision, sizing_adjustment, final_stance, weighted_score,
-- candidate, risk_decision, and opinions are all nullable *together*: a
-- "no strategy is cleared to run in this regime" narrative
-- (narrator.generate_narrative's candidate=None branch) legitimately has
-- none of them, since no candidate ever reached risk_engine or ai_council.

CREATE TABLE IF NOT EXISTS council_narratives (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT NOT NULL,
    strategy_id         TEXT,
    regime              TEXT NOT NULL,
    regime_confidence   DOUBLE PRECISION NOT NULL,
    decision            TEXT CHECK (decision IN ('APPROVE', 'REDUCE', 'REJECT')),
    sizing_adjustment   DOUBLE PRECISION,
    final_stance        TEXT CHECK (final_stance IN ('SUPPORT', 'OPPOSE', 'NEUTRAL', 'VETO')),
    weighted_score      DOUBLE PRECISION,
    narrative           TEXT NOT NULL,
    candidate           JSONB,
    risk_decision       JSONB,
    opinions            JSONB,
    "timestamp"         TIMESTAMPTZ NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_council_narratives_symbol_timestamp
    ON council_narratives (symbol, "timestamp" DESC);
