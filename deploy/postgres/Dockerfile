# Render's managed Postgres product doesn't support the TimescaleDB
# extension every migration in data/migrations/ depends on
# (CREATE EXTENSION timescaledb; create_hypertable(...) on market_ticks,
# ohlcv, orderbook_snapshots, features, funding_rates, futures_basis). This
# self-hosts the exact same image docker-compose.yml already uses locally,
# as a Render private service with a persistent disk, instead.
#
# The official Postgres/Timescale image only runs anything in
# /docker-entrypoint-initdb.d on a truly empty data directory (first boot).
# Copying every migration in there reproduces docker-compose.yml's own
# `./data/migrations:/docker-entrypoint-initdb.d:ro` mount exactly, so the
# schema created here matches local dev byte-for-byte. A migration added
# *after* the first deploy will NOT run automatically — see
# docs/deployment/RENDER-DEPLOYMENT.md's "applying new migrations" section.
FROM timescale/timescaledb:latest-pg16

COPY data/migrations/ /docker-entrypoint-initdb.d/
