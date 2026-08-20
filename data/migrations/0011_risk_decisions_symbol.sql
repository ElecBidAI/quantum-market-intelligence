-- Adds risk_decisions.symbol.
--
-- Found by manual verification of services/ai-council/src/ai_council/
-- run_pipeline.py against real data (not caught by unit tests, which never
-- modeled two symbols sharing a strategy_id + exact timestamp): correlating
-- a signal to its risk decision via strategy_id + timestamp alone is
-- ambiguous whenever two different symbols pick the same strategy in the
-- same pipeline run with bars that share a last-bar timestamp (routine,
-- since OHLCV bars are minute-aligned across symbols) — the join could
-- silently return the wrong symbol's decision.
--
-- NOT NULL going forward, via the DEFAULT-then-drop trick (same as
-- 0010_council_narratives_i18n.sql's narrative_es): existing rows are all
-- local demo/test data, no production rows exist yet, and every row
-- run_pipeline.py writes from now on always supplies a symbol.

ALTER TABLE risk_decisions ADD COLUMN symbol TEXT NOT NULL DEFAULT '';
ALTER TABLE risk_decisions ALTER COLUMN symbol DROP DEFAULT;
CREATE INDEX IF NOT EXISTS idx_risk_decisions_symbol_time ON risk_decisions (symbol, "timestamp" DESC);
