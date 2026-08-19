"""Postgres persistence for paper orders, fills, and portfolio snapshots.

Same injectable-cursor pattern as every other service's persistence.py.
"""

from __future__ import annotations

import json
from typing import Protocol

from paper_execution.fills import Fill
from paper_execution.orders import PaperOrder
from paper_execution.positions import PositionBook


class Cursor(Protocol):
    def execute(self, query: str, params: tuple[object, ...] | None = ...) -> object: ...


def insert_paper_order(cursor: Cursor, order: PaperOrder) -> None:
    cursor.execute(
        """
        INSERT INTO paper_orders
            (order_id, strategy_id, symbol, direction, size_pct, risk_decision_code, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            order.order_id,
            order.strategy_id,
            order.symbol,
            order.direction,
            order.size_pct,
            order.risk_decision_code,
            order.created_at,
        ),
    )


def insert_fill(cursor: Cursor, fill: Fill) -> None:
    cursor.execute(
        """
        INSERT INTO fills (order_id, symbol, direction, size_pct, price, "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (fill.order_id, fill.symbol, fill.direction, fill.size_pct, fill.price, fill.timestamp),
    )


def insert_portfolio_snapshot(
    cursor: Cursor,
    equity: float,
    realized_pnl_total: float,
    book: PositionBook,
    current_prices: dict[str, float],
    timestamp: str,
) -> None:
    positions_json = {
        symbol: {"netSize": p.net_size, "avgEntryPrice": p.avg_entry_price}
        for symbol, p in book.positions.items()
    }
    cursor.execute(
        """
        INSERT INTO portfolio_snapshots
            (equity, realized_pnl_total, unrealized_pnl_total, gross_exposure_pct,
             net_exposure_pct, positions, "timestamp")
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            equity,
            realized_pnl_total,
            book.total_unrealized_pnl(current_prices),
            book.gross_exposure_pct(),
            book.net_exposure_pct(),
            json.dumps(positions_json),
            timestamp,
        ),
    )
