"""Batch entry point: compute features for the Phase 1 universe and upsert them.

Deliberately a one-shot batch job, not a long-running daemon — run it on a
schedule (cron, systemd timer, etc.) once there's an operational reason to
pick a cadence. Wiring it into a live stream is deferred until
strategy-engine (a real consumer) exists; polling avoids guessing at a
cadence nothing consumes yet.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime

import psycopg

from feature_engine.db import fetch_recent_ohlcv, upsert_features
from feature_engine.features import FEATURE_SET, SCHEMA_VERSION, compute_features

# Mirrors services/market-data/src/symbols.ts's Phase 1 universe. Kept as its
# own constant rather than a cross-service import, same rationale as
# apps/api/src/routes/market.ts: services only share state through Postgres,
# not code.
SYMBOLS = ["BTC-USDT", "ETH-USDT"]
INTERVAL = "1m"
LOOKBACK_BARS = 200


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as conn, conn.cursor() as cursor:
        for symbol in SYMBOLS:
            bars = fetch_recent_ohlcv(cursor, symbol, INTERVAL, LOOKBACK_BARS)
            if not bars:
                msg = f"[feature-engine] no bars yet for {symbol} {INTERVAL}; skipping"
                print(msg, file=sys.stderr)
                continue

            features = compute_features(bars, INTERVAL)
            timestamp = features.pop("timestamp")
            features.pop("feature_set")

            upsert_features(
                cursor,
                symbol=symbol,
                interval=INTERVAL,
                feature_set=FEATURE_SET,
                schema_version=SCHEMA_VERSION,
                timestamp=timestamp,
                computed_at=datetime.now(UTC).isoformat(),
                features=features,
            )
            print(f"[feature-engine] wrote features for {symbol} {INTERVAL} @ {timestamp}")
        conn.commit()


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    run(database_url)


if __name__ == "__main__":
    main()
