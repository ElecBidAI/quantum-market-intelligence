"""Futures/perpetuals calculators (brief Section 12, brief Section 11 "Financial Calculators").

Options (Black-Scholes, Greeks, implied volatility, term structure, smile/skew)
are explicitly out of scope for this module — brief Section 12 itself defers
them ("Options phase") and the Phase 9 task list says "options later." They
get their own module once that phase starts, rather than being bolted on
half-finished here.

`liquidation_price` uses the standard simplified isolated-margin formula
(entry adjusted by initial margin minus maintenance margin). It ignores fees
and funding accrual between now and liquidation — a real exchange's engine
accounts for both, so this is a planning/risk-budgeting estimate, not the
exact price an exchange would report. Documenting the simplification here is
the same "no unrealistic fills" discipline `backtester`/`paper_execution`
apply to trade simulation, applied to a formula instead of a fill.
"""

from __future__ import annotations


def basis(spot_price: float, futures_price: float) -> float:
    """Absolute basis: futures_price - spot_price (positive = contango)."""
    if spot_price <= 0 or futures_price <= 0:
        raise ValueError("spot_price and futures_price must be positive")
    return futures_price - spot_price


def basis_pct(spot_price: float, futures_price: float) -> float:
    """Basis as a fraction of spot price."""
    if spot_price <= 0 or futures_price <= 0:
        raise ValueError("spot_price and futures_price must be positive")
    return (futures_price - spot_price) / spot_price


def annualized_basis(spot_price: float, futures_price: float, days_to_expiry: float) -> float:
    """Basis annualized by simple (non-compounded) scaling to a 365-day year.

    For a *dated* future only — a perpetual has no expiry to scale by; use
    `annualized_funding_rate` for perpetuals instead.
    """
    if days_to_expiry <= 0:
        raise ValueError("days_to_expiry must be positive")
    return basis_pct(spot_price, futures_price) * (365 / days_to_expiry)


def annualized_funding_rate(funding_rate: float, fundings_per_day: float = 3.0) -> float:
    """Annualizes a perpetual funding rate (Binance: 3 fundings/day, every 8h, by default).

    Perpetuals have no expiry, so `annualized_basis`'s days-to-expiry scaling
    doesn't apply — a perpetual's basis is driven by (and converges toward)
    accumulated funding instead, so that's what's annualized here.
    """
    if fundings_per_day <= 0:
        raise ValueError("fundings_per_day must be positive")
    return funding_rate * fundings_per_day * 365


def funding_pnl(position_notional: float, funding_rate: float, direction: int) -> float:
    """PnL from one funding payment. direction: 1 = long, -1 = short.

    A positive funding_rate means longs pay shorts (the usual convention
    when perpetual price trades above the index) — so a long's PnL is
    negative when funding_rate is positive, and a short's is positive.
    """
    if direction not in (1, -1):
        raise ValueError("direction must be 1 (long) or -1 (short)")
    return -direction * position_notional * funding_rate


def leverage(notional: float, equity: float) -> float:
    """Notional exposure divided by posted equity."""
    if equity <= 0:
        raise ValueError("equity must be positive")
    if notional < 0:
        raise ValueError("notional must be non-negative")
    return notional / equity


def liquidation_price(
    entry_price: float, leverage_: float, direction: int, maintenance_margin_rate: float
) -> float:
    """Simplified isolated-margin liquidation price (see module docstring for what it ignores)."""
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if leverage_ <= 0:
        raise ValueError("leverage_ must be positive")
    if direction not in (1, -1):
        raise ValueError("direction must be 1 (long) or -1 (short)")
    if not 0 <= maintenance_margin_rate < 1:
        raise ValueError("maintenance_margin_rate must be in [0, 1)")

    initial_margin_rate = 1 / leverage_
    if direction == 1:
        return entry_price * (1 - initial_margin_rate + maintenance_margin_rate)
    return entry_price * (1 + initial_margin_rate - maintenance_margin_rate)


def liquidation_buffer_pct(current_price: float, liq_price: float, direction: int) -> float:
    """Fraction current_price would have to move (adversely) to reach liquidation."""
    if current_price <= 0:
        raise ValueError("current_price must be positive")
    if direction not in (1, -1):
        raise ValueError("direction must be 1 (long) or -1 (short)")
    if direction == 1:
        return (current_price - liq_price) / current_price
    return (liq_price - current_price) / current_price


def open_interest_change(previous_oi: float, current_oi: float) -> float:
    """Absolute change in open interest between two observations."""
    if previous_oi < 0 or current_oi < 0:
        raise ValueError("open interest must be non-negative")
    return current_oi - previous_oi


def open_interest_change_pct(previous_oi: float, current_oi: float) -> float:
    """Fractional change in open interest between two observations."""
    if previous_oi <= 0:
        raise ValueError("previous_oi must be positive")
    if current_oi < 0:
        raise ValueError("current_oi must be non-negative")
    return (current_oi - previous_oi) / previous_oi
