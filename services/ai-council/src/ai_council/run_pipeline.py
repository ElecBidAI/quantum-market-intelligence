"""Batch entry point: run the full regime -> strategy -> risk -> council ->
paper-execution chain against real ingested bars and persist everything it
produces (renamed from run_narrative.py — its scope grew from "compute a
narrative" to "run the full demo pipeline").

Deliberately a one-shot batch job, not a long-running daemon — same
rationale as services/feature-engine/src/feature_engine/main.py: run it on
a schedule (cron, systemd timer, etc.) once there's an operational reason
to pick a cadence.

DEMO/PLACEHOLDER NOTICE: the sizing and risk figures in every generated
narrative assume a fixed $100,000 paper `PortfolioState` and default
`RiskLimits()` — there is no real portfolio-engine wiring yet, so this is
not, and must never be read as, any user's actual account. `narrator.py`'s
`DISCLAIMER_EN`/`DISCLAIMER_ES` restate this in every narrative produced;
this notice is the source-of-truth for *why* that sentence exists.

Every symbol gets **both** an English and a Spanish narrative, rendered
from the same pipeline run (`narrator.generate_narrative` is called twice,
once per language, against the same regime/candidate/decision/opinions/
thesis — the pipeline itself never runs twice).

This is the first thing in this repository that runs the full
regime->strategy->risk->council chain against real Postgres-ingested bars
(everything before this was proven only against synthetic fixtures in
integration tests) — see docs/architecture/QMI-MASTER-ARCHITECTURE.md
Section 6. As of this revision it's also the first time
`paper_execution` runs against that same real chain, instead of only its
own test's synthetic fixtures.

**Positions are always replayed from the `fills` ledger, never carried in
memory across runs** — this process starts fresh every invocation, so
before touching any symbol it rebuilds the current `PositionBook` from
every fill ever recorded (`paper_execution.positions.replay_positions`),
applies whatever new fill this run produces, then persists one
`portfolio_snapshots` row reflecting the result. Rebuilding from the
ledger every time means there's no incrementally-maintained state that
could ever drift from it — `paper_execution.positions.reconcile()` exists
for exactly the drift this design avoids by construction, so it isn't
used here.

**Known limitation, not silently wrong**: every run that gets an
APPROVE/REDUCE decision creates a *new* paper order/fill — there is no
de-duplication against an already-open position for the same
strategy/symbol/direction. Fine for a manually-triggered demo script that
nothing schedules yet; would need addressing before this ever runs
unattended on a cadence.
"""

from __future__ import annotations

import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime

import psycopg
from paper_execution.fills import FillSimulator
from paper_execution.orders import create_order_from_decision
from paper_execution.persistence import insert_fill, insert_paper_order, insert_portfolio_snapshot
from paper_execution.positions import replay_positions
from regime_engine.classify import classify_regime
from regime_engine.thresholds import RegimeThresholds
from risk_engine.engine import evaluate
from risk_engine.limits import RiskLimits
from risk_engine.state import MarketContext, PortfolioState
from strategy_engine.engine import run_strategies
from strategy_engine.risk_adapter import candidate_to_risk_request
from strategy_engine.strategies import (
    BreakoutStrategy,
    MeanReversionStrategy,
    TrendFollowingStrategy,
)

from ai_council.agents import Auditor, DevilsAdvocate, QuantAgent, RiskOfficer
from ai_council.context import CouncilContext
from ai_council.council import run_council, synthesize
from ai_council.db import (
    fetch_all_fills,
    fetch_recent_ohlcv,
    insert_narrative,
    insert_risk_decision,
    insert_signal,
)
from ai_council.narrator import generate_narrative

# Mirrors services/market-data/src/symbols.ts's Phase 1 universe. Kept as
# its own constant rather than a cross-service import, same rationale as
# feature_engine.main and apps/api/src/routes/market.ts.
SYMBOLS = ["BTC-USDT", "ETH-USDT"]
INTERVAL = "1m"
LOOKBACK_BARS = 200

STRATEGIES = [TrendFollowingStrategy(), MeanReversionStrategy(), BreakoutStrategy()]
AGENTS = [QuantAgent(), RiskOfficer(), DevilsAdvocate(), Auditor()]
THRESHOLDS = RegimeThresholds()

# Placeholder demo account — see module docstring.
PORTFOLIO = PortfolioState(equity=100_000.0)
LIMITS = RiskLimits()
REQUESTED_SIZE_PCT = 0.02
MARKET = MarketContext(spread_bps=5.0, data_age_seconds=1.0)
FILL_SIMULATOR = FillSimulator(spread_bps=5.0, slippage_bps=5.0)


def _pick_candidate(candidates: list[dict]) -> dict | None:
    """Highest expectedEdge wins; ties broken by strategyId ascending. Callers
    (narrator.generate_narrative via candidate_pool_size) are told how many
    candidates existed, so this pick is disclosed, never silent."""
    if not candidates:
        return None
    return sorted(candidates, key=lambda c: (-c["expectedEdge"], c["strategyId"]))[0]


def run(database_url: str) -> None:
    with psycopg.connect(database_url) as conn, conn.cursor() as cursor:
        book = replay_positions(fetch_all_fills(cursor))
        current_prices: dict[str, float] = {}

        for symbol in SYMBOLS:
            bars = fetch_recent_ohlcv(cursor, symbol, INTERVAL, LOOKBACK_BARS)
            if not bars:
                msg = f"[ai-council] no bars yet for {symbol} {INTERVAL}; skipping"
                print(msg, file=sys.stderr)
                continue
            current_prices[symbol] = bars[-1]["close"]

            regime = classify_regime(bars, THRESHOLDS)
            candidates = run_strategies(STRATEGIES, bars, regime, symbol, venue="binance")
            candidate = _pick_candidate(candidates)

            if candidate is None:
                narrative_en = generate_narrative(
                    symbol, regime, None, None, [], None, language="en"
                )
                narrative_es = generate_narrative(
                    symbol, regime, None, None, [], None, language="es"
                )
                insert_narrative(
                    cursor,
                    symbol=symbol,
                    strategy_id=None,
                    regime=regime.label,
                    regime_confidence=regime.confidence,
                    decision=None,
                    sizing_adjustment=None,
                    final_stance=None,
                    weighted_score=None,
                    narrative_en=narrative_en,
                    narrative_es=narrative_es,
                    candidate=None,
                    risk_decision=None,
                    opinions=None,
                    timestamp=bars[-1]["timestamp"],
                )
                print(f"[ai-council] wrote no-candidate narrative for {symbol} {regime.label}")
                continue

            request = candidate_to_risk_request(candidate, REQUESTED_SIZE_PCT)
            decision = evaluate(
                request,
                PORTFOLIO,
                MARKET,
                LIMITS,
                now=datetime.fromisoformat(candidate["timestamp"]),
            )
            insert_signal(cursor, candidate)
            insert_risk_decision(cursor, decision, symbol)

            context = CouncilContext(candidate=candidate, regime=regime, risk_decision=decision)
            opinions = run_council(AGENTS, context)
            thesis = synthesize(opinions)
            pool_size = len(candidates)
            narrative_en = generate_narrative(
                symbol,
                regime,
                candidate,
                decision,
                opinions,
                thesis,
                candidate_pool_size=pool_size,
                language="en",
            )
            narrative_es = generate_narrative(
                symbol,
                regime,
                candidate,
                decision,
                opinions,
                thesis,
                candidate_pool_size=pool_size,
                language="es",
            )

            insert_narrative(
                cursor,
                symbol=symbol,
                strategy_id=candidate["strategyId"],
                regime=regime.label,
                regime_confidence=regime.confidence,
                decision=decision["decision"],
                sizing_adjustment=decision["sizingAdjustment"],
                final_stance=thesis.final_stance,
                weighted_score=thesis.weighted_score,
                narrative_en=narrative_en,
                narrative_es=narrative_es,
                candidate=dict(candidate),
                risk_decision=decision,
                opinions=[asdict(o) for o in opinions],
                timestamp=candidate["timestamp"],
            )
            print(f"[ai-council] wrote narrative for {symbol} @ {candidate['timestamp']}")

            if decision["decision"] in ("APPROVE", "REDUCE"):
                order = create_order_from_decision(candidate, decision, REQUESTED_SIZE_PCT)
                fill = FILL_SIMULATOR.simulate_fill(
                    order, market_price=current_prices[symbol], timestamp=candidate["timestamp"]
                )
                book.apply_fill(fill)
                insert_paper_order(cursor, order)
                insert_fill(cursor, fill)
                print(f"[ai-council] wrote paper order+fill for {symbol} @ {fill.price:.2f}")

        insert_portfolio_snapshot(
            cursor,
            equity=PORTFOLIO.equity,
            realized_pnl_total=book.realized_pnl_total,
            book=book,
            current_prices=current_prices,
            timestamp=datetime.now(UTC).isoformat(),
        )
        print(f"[ai-council] wrote portfolio snapshot ({len(book.positions)} open position(s))")
        conn.commit()


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")
    run(database_url)


if __name__ == "__main__":
    main()
