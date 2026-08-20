-- QMI Phase 9 schema: perpetual futures market data ingested by
-- services/market-data's BinanceFuturesAdapter.
--
-- Mirrors the contracts in packages/contracts/src/derivatives.ts. Only
-- funding rate and futures-vs-index basis are ingested (both derived from
-- Binance's public @markPrice@1s stream, no API key required). Open
-- interest and liquidation-event tables are NOT created here: this service
-- has no producer for either yet (open interest is REST-poll only on
-- Binance, and this service is WebSocket-push only; liquidation events
-- require the separate @forceOrder stream, not yet wired). Both are
-- deferred until a real producer exists, per the same pattern used for
-- orderbook_deltas in 0002_market_data.sql.

-- Funding rate (DATA-CONTRACTS.md derivatives section; packages/contracts/src/derivatives.ts).
CREATE TABLE IF NOT EXISTS funding_rates (
    "timestamp"      TIMESTAMPTZ NOT NULL,
    source           TEXT NOT NULL,
    exchange         TEXT NOT NULL,
    symbol           TEXT NOT NULL,
    ingested_at      TIMESTAMPTZ NOT NULL,
    quality_status   TEXT NOT NULL CHECK (quality_status IN ('ok', 'suspect', 'rejected')),
    schema_version   INTEGER NOT NULL,
    rate             DOUBLE PRECISION NOT NULL,
    interval_hours   DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (exchange, symbol, "timestamp")
);

CREATE INDEX IF NOT EXISTS idx_funding_rates_symbol_time ON funding_rates (symbol, "timestamp" DESC);

-- Futures-vs-index basis, sampled once per markPrice tick (~1s). Perpetuals
-- have no expiry, so `annualized_basis` here is left as raw basis percentage
-- (see binance-futures-parsers.ts); the economically meaningful annualized
-- figure is quant_core.derivatives.annualized_funding_rate instead.
CREATE TABLE IF NOT EXISTS futures_basis (
    "timestamp"       TIMESTAMPTZ NOT NULL,
    source            TEXT NOT NULL,
    exchange          TEXT NOT NULL,
    symbol            TEXT NOT NULL,
    ingested_at       TIMESTAMPTZ NOT NULL,
    quality_status    TEXT NOT NULL CHECK (quality_status IN ('ok', 'suspect', 'rejected')),
    schema_version    INTEGER NOT NULL,
    spot_price        DOUBLE PRECISION NOT NULL,
    futures_price     DOUBLE PRECISION NOT NULL,
    basis             DOUBLE PRECISION NOT NULL,
    annualized_basis  DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (exchange, symbol, "timestamp")
);

CREATE INDEX IF NOT EXISTS idx_futures_basis_symbol_time ON futures_basis (symbol, "timestamp" DESC);
