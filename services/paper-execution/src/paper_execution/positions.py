"""Position tracking from a stream of fills.

Standard weighted-average-entry-price accounting: a fill in the same
direction as the existing position averages into the entry price; a fill in
the opposite direction closes (fully or partially) against the existing
entry price, realizing PnL for the closed portion; a fill larger than the
existing position closes it entirely and opens a new position in the other
direction at the fill price ("flipping").

Every closed portion appends a *fractional* return (not a currency amount)
to `closed_trade_returns`, so it's directly usable with
`backtester.metrics`'s win_rate/expectancy/payoff_ratio/profit_factor —
those expect the same convention `backtester.engine`'s round-trip trades
use.
"""

from __future__ import annotations

from dataclasses import dataclass

from paper_execution.fills import Fill


@dataclass
class Position:
    symbol: str
    net_size: float  # signed: positive=net long, negative=net short (fraction of equity)
    avg_entry_price: float
    realized_pnl: float = 0.0

    def unrealized_pnl(self, current_price: float) -> float:
        return self.net_size * (current_price - self.avg_entry_price)


class PositionBook:
    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}
        self.realized_pnl_total: float = 0.0
        self.closed_trade_returns: list[float] = []

    def apply_fill(self, fill: Fill) -> None:
        if fill.price <= 0:
            raise ValueError("fill.price must be positive")
        signed_size = fill.size_pct if fill.direction == "LONG" else -fill.size_pct

        existing = self.positions.get(fill.symbol)
        if existing is None or existing.net_size == 0:
            self.positions[fill.symbol] = Position(fill.symbol, signed_size, fill.price)
            return

        same_direction = (existing.net_size > 0 and signed_size > 0) or (
            existing.net_size < 0 and signed_size < 0
        )
        if same_direction:
            new_size = existing.net_size + signed_size
            existing.avg_entry_price = (
                existing.avg_entry_price * abs(existing.net_size) + fill.price * abs(signed_size)
            ) / abs(new_size)
            existing.net_size = new_size
            return

        # Opposite direction: closes some or all of the existing position, possibly flipping.
        closing_size = min(abs(existing.net_size), abs(signed_size))
        position_sign = 1 if existing.net_size > 0 else -1
        price_delta = fill.price - existing.avg_entry_price
        trade_return = position_sign * price_delta / existing.avg_entry_price
        realized = closing_size * price_delta * position_sign

        existing.realized_pnl += realized
        self.realized_pnl_total += realized
        self.closed_trade_returns.append(trade_return)

        is_flip = abs(signed_size) > abs(existing.net_size)
        new_size = existing.net_size + signed_size
        if is_flip:
            existing.avg_entry_price = fill.price
        existing.net_size = new_size

        if existing.net_size == 0:
            del self.positions[fill.symbol]

    def gross_exposure_pct(self) -> float:
        return sum(abs(p.net_size) for p in self.positions.values())

    def net_exposure_pct(self) -> float:
        return sum(p.net_size for p in self.positions.values())

    def total_unrealized_pnl(self, current_prices: dict[str, float]) -> float:
        total = 0.0
        for symbol, position in self.positions.items():
            if symbol not in current_prices:
                raise ValueError(f"missing current price for open position {symbol!r}")
            total += position.unrealized_pnl(current_prices[symbol])
        return total


@dataclass(frozen=True)
class Discrepancy:
    symbol: str
    live_net_size: float
    replayed_net_size: float


def replay_positions(fills: list[Fill]) -> PositionBook:
    """Rebuilds a PositionBook from scratch by replaying every fill in order."""
    book = PositionBook()
    for fill in fills:
        book.apply_fill(fill)
    return book


def reconcile(
    live_book: PositionBook, fills: list[Fill], tolerance: float = 1e-9
) -> list[Discrepancy]:
    """Compares `live_book` (incrementally maintained) against a from-scratch replay of `fills`.

    A discrepancy means the live book drifted from what the fill ledger
    actually says happened — e.g. a missed, duplicated, or corrupted fill
    application. This is the reconciliation brief Section 19 asks for: an
    independent recomputation checked against the running state, not just
    trusting the running state.
    """
    replayed = replay_positions(fills)
    symbols = set(live_book.positions) | set(replayed.positions)

    discrepancies = []
    for symbol in symbols:
        live_size = live_book.positions[symbol].net_size if symbol in live_book.positions else 0.0
        replayed_size = (
            replayed.positions[symbol].net_size if symbol in replayed.positions else 0.0
        )
        if abs(live_size - replayed_size) > tolerance:
            discrepancies.append(Discrepancy(symbol, live_size, replayed_size))
    return sorted(discrepancies, key=lambda d: d.symbol)
