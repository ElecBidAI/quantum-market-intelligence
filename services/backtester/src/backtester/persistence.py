"""Postgres persistence for backtest results and experiment records.

Same injectable-cursor pattern as services/feature-engine/src/feature_engine/db.py:
anything exposing `.execute(sql, params)` works, so tests never touch a real
database.
"""

from __future__ import annotations

import json
from typing import Protocol

from backtester.experiment import ExperimentRecord


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[object, ...] | None = ...) -> object: ...


def insert_backtest(
    cursor: Cursor,
    strategy_id: str,
    symbol: str,
    interval: str,
    dataset_version: str,
    parameters: dict[str, object],
    cost_assumptions: dict[str, object],
    metrics: dict[str, object],
    created_at: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO backtests
            (strategy_id, symbol, interval, dataset_version, parameters,
             cost_assumptions, metrics, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            strategy_id,
            symbol,
            interval,
            dataset_version,
            json.dumps(parameters),
            json.dumps(cost_assumptions),
            json.dumps(metrics),
            created_at,
        ),
    )


def insert_research_run(cursor: Cursor, record: ExperimentRecord, created_at: str) -> None:
    cursor.execute(
        """
        INSERT INTO research_runs
            (hypothesis, dataset_version, transformations, model_or_formula, parameters,
             cost_assumptions, backtest_summary, walk_forward_summary, monte_carlo_summary,
             stress_test_summary, risk_review, conclusion, status, tags, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            record.hypothesis,
            record.dataset_version,
            json.dumps(record.transformations),
            record.model_or_formula,
            json.dumps(record.parameters),
            json.dumps(record.cost_assumptions),
            json.dumps(record.backtest_summary),
            json.dumps(record.walk_forward_summary),
            json.dumps(record.monte_carlo_summary),
            json.dumps(record.stress_test_summary),
            json.dumps(record.risk_review),
            record.conclusion,
            record.status,
            json.dumps(record.tags),
            created_at,
        ),
    )
