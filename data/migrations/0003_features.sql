-- QMI Phase 2 schema: computed feature vectors (services/feature-engine).
--
-- One row per (symbol, interval, feature_set, timestamp). `feature_set`
-- names the exact set of feature-engine/src/feature_engine/features.py logic
-- that produced the row (currently "phase2-v1"), so a later, incompatible
-- feature set can be introduced without silently reinterpreting old rows.

CREATE TABLE IF NOT EXISTS features (
    "timestamp"      TIMESTAMPTZ NOT NULL,
    symbol           TEXT NOT NULL,
    interval         TEXT NOT NULL,
    feature_set      TEXT NOT NULL,
    schema_version   INTEGER NOT NULL,
    computed_at      TIMESTAMPTZ NOT NULL,
    features         JSONB NOT NULL,
    PRIMARY KEY (symbol, interval, feature_set, "timestamp")
);

CREATE INDEX IF NOT EXISTS idx_features_symbol_interval_time
    ON features (symbol, interval, "timestamp" DESC);
