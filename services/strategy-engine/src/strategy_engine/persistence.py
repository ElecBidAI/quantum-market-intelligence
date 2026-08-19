"""Postgres persistence for strategy candidates.

Writes into the `signals` table, which has existed since Phase 0
(data/migrations/0001_init.sql) — it was created before there was any
producer for it, on the expectation that strategy-engine would eventually
be that producer. Same injectable-cursor pattern as every other service's
persistence.py.
"""

from __future__ import annotations

import json
from typing import Protocol

from strategy_engine.strategy import StrategyCandidate


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[object, ...] | None = ...) -> object: ...


def insert_signal(cursor: Cursor, candidate: StrategyCandidate) -> None:
    cursor.execute(
        """
        INSERT INTO signals
            (strategy_id, symbol, venue, direction, horizon, signal_strength,
             entry_logic, invalidation_logic, stop_logic, target_logic,
             expected_edge, estimated_costs, regime, "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            candidate["strategyId"],
            candidate["symbol"],
            candidate["venue"],
            candidate["direction"],
            candidate["horizon"],
            candidate["signalStrength"],
            json.dumps(candidate["entryLogic"]),
            json.dumps(candidate["invalidationLogic"]),
            json.dumps(candidate["stopLogic"]),
            json.dumps(candidate["targetLogic"]),
            candidate["expectedEdge"],
            candidate["estimatedCosts"],
            candidate["regime"],
            candidate["timestamp"],
        ),
    )
