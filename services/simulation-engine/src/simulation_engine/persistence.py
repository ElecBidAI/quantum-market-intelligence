"""Postgres persistence for simulation runs.

Same injectable-cursor pattern as the other services' db.py/persistence.py
modules — tests never touch a real database.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Protocol

from simulation_engine.monte_carlo import MonteCarloResult


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[object, ...] | None = ...) -> object: ...


def insert_simulation_run(
    cursor: Cursor,
    run_type: str,
    strategy_id: str | None,
    dataset_version: str,
    parameters: dict[str, object],
    results: dict[str, object],
    created_at: str,
) -> None:
    cursor.execute(
        """
        INSERT INTO simulation_runs
            (run_type, strategy_id, dataset_version, parameters, results, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            run_type,
            strategy_id,
            dataset_version,
            json.dumps(parameters),
            json.dumps(results),
            created_at,
        ),
    )


def monte_carlo_result_to_json(result: MonteCarloResult) -> dict[str, object]:
    """Converts a MonteCarloResult to a JSON-safe dict (dict keys must be strings)."""
    data = asdict(result)
    data["terminal_multiplier_percentiles"] = {
        str(k): v for k, v in result.terminal_multiplier_percentiles.items()
    }
    return data
