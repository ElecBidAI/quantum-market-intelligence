-- QMI Phase 1 schema: raw market data ingested by services/market-data.
--
-- Mirrors the contracts in packages/contracts/src/market.ts and
-- docs/architecture/DATA-CONTRACTS.md Sections 2-3. Created now (Phase 1)
-- rather than in 0001_init.sql because this is the phase that first reads
-- and writes these tables (see DATA-CONTRACTS.md Section 9).
--
-- All timestamps are TIMESTAMPTZ, written in UTC. TimescaleDB hypertables
-- are used for the append-only, time-ordered tables so ingestion volume can
-- grow without a schema change.

-- Trade / tick (DATA-CONTRACTS.md Section 3.1).
CREATE TABLE IF NOT EXISTS market_ticks (
    "timestamp"      TIMESTAMPTZ NOT NULL,
    source           TEXT NOT NULL,
    exchange         TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    ingested_at      TIMESTAMPTZ NOT NULL,
    quality_status   TEXT NOT NULL CHECK (quality_status IN ('ok', 'suspect', 'rejected')),
    schema_version   INTEGER NOT NULL,
    price            DOUBLE PRECISION NOT NULL,
    size             DOUBLE PRECISION NOT NULL,
    side             TEXT NOT NULL CHECK (side IN ('buy', 'sell', 'unknown')),
    trade_id         TEXT NOT NULL,
    PRIMARY KEY (exchange, symbol, trade_id, "timestamp")
);

SELECT create_hypertable('market_ticks', by_range('timestamp'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_market_ticks_symbol_time ON market_ticks (symbol, "timestamp" DESC);

-- OHLCV bar (DATA-CONTRACTS.md Section 3.2). Only closed bars are inserted;
-- services/market-data never persists an in-progress bar as if it were final.
CREATE TABLE IF NOT EXISTS ohlcv (
    "timestamp"      TIMESTAMPTZ NOT NULL,
    source           TEXT NOT NULL,
    exchange         TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    ingested_at      TIMESTAMPTZ NOT NULL,
    quality_status   TEXT NOT NULL CHECK (quality_status IN ('ok', 'suspect', 'rejected')),
    schema_version   INTEGER NOT NULL,
    interval         TEXT NOT NULL,
    open             DOUBLE PRECISION NOT NULL,
    high             DOUBLE PRECISION NOT NULL,
    low              DOUBLE PRECISION NOT NULL,
    close            DOUBLE PRECISION NOT NULL,
    volume           DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (exchange, symbol, interval, "timestamp")
);

SELECT create_hypertable('ohlcv', by_range('timestamp'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol_interval_time ON ohlcv (symbol, interval, "timestamp" DESC);

-- Order-book snapshot (DATA-CONTRACTS.md Section 3.4). Phase 1 ingests
-- top-of-book snapshots only (e.g. Binance partial-depth stream); full
-- incremental order-book reconstruction from orderbook_deltas (Section 3.5,
-- with sequence-gap detection) is deferred to a later phase, so that table
-- is not created until a producer exists for it.
CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    "timestamp"      TIMESTAMPTZ NOT NULL,
    source           TEXT NOT NULL,
    exchange         TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    ingested_at      TIMESTAMPTZ NOT NULL,
    quality_status   TEXT NOT NULL CHECK (quality_status IN ('ok', 'suspect', 'rejected')),
    schema_version   INTEGER NOT NULL,
    bids             JSONB NOT NULL,
    asks             JSONB NOT NULL,
    sequence_id      BIGINT NOT NULL,
    PRIMARY KEY (exchange, symbol, sequence_id, "timestamp")
);

SELECT create_hypertable('orderbook_snapshots', by_range('timestamp'), if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_orderbook_snapshots_symbol_time ON orderbook_snapshots (symbol, "timestamp" DESC);
