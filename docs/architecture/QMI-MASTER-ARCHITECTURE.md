# QMI — Master Architecture

Status: Phase 0 (Foundation). This document describes the target architecture for
Quantum Market Intelligence (QMI) and the subset that exists today.

## 1. Purpose

QMI is a quantitative market intelligence platform, crypto-first and multi-asset-ready.
It ingests live/historical market data, computes statistical and financial features,
generates and evaluates strategy candidates, quantifies risk, backtests/simulates, and
supports paper trading. Live execution is out of scope until Phase 10 and requires
explicit human approval.

**Core rule: no AI agent, signal, strategy, or model may bypass the Risk Engine.**
Every strategy candidate is a proposal, never an executable order, until the Risk
Engine returns `APPROVE` or `REDUCE`.

## 2. Guiding pipeline

```
Data → Quality → Mathematics → Statistical Evidence → Regime → Strategy Candidate
  → Risk → Portfolio → Simulation → Paper Execution → Measurement → Learning
```

Real execution is only considered after this pipeline is validated end to end in
paper mode.

## 3. Monorepo layout

```
qmi/
  apps/
    web/                # Next.js + TypeScript dashboard
    api/                # API gateway / auth / orchestration
  services/
    market-data/         # exchange adapters, websocket ingestion
    feature-engine/       # normalized quantitative features
    statistical-engine/   # descriptive/inferential statistics
    forecast-engine/       # time-series/probabilistic forecasting
    microstructure-engine/ # order book/order flow/liquidity
    regime-engine/         # market regime classification
    strategy-engine/       # signal/strategy generation
    risk-engine/            # mandatory approval/rejection layer
    portfolio-engine/       # allocation/optimization/exposure
    simulation-engine/      # Monte Carlo/bootstrap/stress
    backtester/             # historical testing/walk-forward
    ai-council/              # analytical agents; no execution authority
    paper-execution/         # simulated order/fill engine
    execution/                # future isolated live execution service (Phase 10+)
  packages/
    contracts/            # shared schemas/types (source of truth for data shapes)
    quant-core/            # reusable, tested quantitative formulas (Python)
    config/                # environment/config loading and validation
    observability/          # structured logging, metrics, tracing helpers
  data/
    migrations/            # SQL migrations (PostgreSQL/TimescaleDB)
    seeds/                  # local/dev seed data (never live market data)
  research/
    notebooks/
    experiments/
  docs/
    architecture/
    formulas/
    api/
    risk/
  tests/
    unit/
    integration/
    quantitative/
    regression/
```

Only `packages/contracts`, `packages/config`, `packages/observability`,
`packages/quant-core`, a minimal `apps/api` health service, a minimal `apps/web`
placeholder, and `data/migrations/0001_init.sql` are implemented in Phase 0. All other
directories exist as placeholders (`README.md` stubs) to fix the intended structure
without pretending the functionality exists.

## 4. Stack decisions (Phase 0)

- **Web**: Next.js (App Router) + TypeScript. Package manager: pnpm workspaces.
- **API gateway**: Fastify + TypeScript (lightweight, typed, good for a thin
  orchestration layer that will later proxy to Python services).
- **Quantitative services**: Python 3.12. Phase 0 ships only `packages/quant-core`
  (pure functions + pytest). Services under `services/*` are scaffolding for later
  phases and are not implemented yet.
- **Database**: PostgreSQL with the TimescaleDB extension for time-series tables.
  ClickHouse is a documented future option for very high-cardinality tick data but is
  not part of Phase 0.
- **Cache/ephemeral state**: Redis.
- **Event streaming**: no concrete choice is wired up yet. The `packages/contracts`
  event schemas are written to be transport-agnostic so NATS, Kafka, or Redis Streams
  can be adopted later without reshaping the payloads.
- **Local dev**: Docker Compose (`docker-compose.yml`) runs Postgres/TimescaleDB and
  Redis. Application processes run on the host during Phase 0 for fast iteration.

## 5. Service boundaries and dependency rules

- **Research/quant logic stays independent of UI.** `packages/quant-core` and future
  `services/*-engine` packages must not import from `apps/web` or `apps/api`.
- **Exchange adapters live behind a common interface** in `services/market-data`
  (Phase 1). No other service talks to an exchange directly.
- **The Risk Engine is the only service allowed to turn a strategy candidate into
  something a paper/live execution service will act on.** `strategy-engine` produces
  candidates; `risk-engine` returns `APPROVE | REDUCE | REJECT`; only approved/reduced
  candidates may reach `paper-execution` (or, later, `execution`).
- **AI Council agents (`services/ai-council`) analyze; they never execute.** Their
  output feeds the Strategy/Risk pipeline like any other evidence source.
- **All timestamps are UTC** at every layer (ingestion, storage, API, UI display may
  localize, but the source of truth is UTC).

## 6. Data flow (target, post-Phase 1)

```
Exchange WS/REST
  → market-data (normalize, dedupe, timestamp, quality-tag)
  → persistence (market_ticks, ohlcv, orderbook_snapshots/deltas)
  → feature-engine / statistical-engine / microstructure-engine
  → forecast-engine, regime-engine
  → strategy-engine (candidate trade objects)
  → risk-engine (APPROVE | REDUCE | REJECT, machine-readable reasons)
  → portfolio-engine (sizing/allocation under risk budget)
  → paper-execution (simulated fills)
  → analytics / research notebook / audit trail
```

## 7. Observability

`packages/observability` provides a structured JSON logger (level, service name,
timestamp, correlation fields) used by every app/service. Metrics and tracing
exporters are not implemented in Phase 0; the package is structured so they can be
added without changing call sites.

## 8. CI

`.github/workflows/ci.yml` runs, on every push/PR:

1. Install (pnpm for the Node workspace, pip for `packages/quant-core`).
2. Lint (ESLint for TS, ruff for Python).
3. Typecheck (`tsc --noEmit` across the TS workspace).
4. Test (vitest for TS packages/apps, pytest for `quant-core`).
5. Build (`next build` for `apps/web`, `tsc build` for `apps/api` and TS packages).

A failure in any step fails CI. There is no deploy step yet — Phase 0 has no
execution capability to deploy.

## 9. Security & governance posture (Phase 0)

See [`docs/risk/RISK-GOVERNANCE.md`](../risk/RISK-GOVERNANCE.md) for the full policy.
In short: paper trading only, no live-money execution code exists anywhere in the
repository, no secrets are committed (`.env.example` documents required variables;
real values stay in untracked `.env` files or a secrets manager), and every risk
decision will be logged immutably once the Risk Engine exists (Phase 3+).

## 10. Non-goals for this phase

Matches [Section 24 of the implementation brief]: no profitability claims, no
auto-trading, no invented market data, no exchange-specific logic scattered through
the codebase, no indicator sprawl before the data/testing foundation is solid. Phase 0
adds no trading logic at all — only the foundation it will be built on.

## 11. Open decisions (deliberately deferred)

- Event streaming transport (NATS vs Kafka vs Redis Streams) — deferred to when a
  second consumer of market-data events actually exists.
- ClickHouse vs TimescaleDB-only for tick-level data — deferred to Phase 1 based on
  measured ingestion volume.
- Python service framework (FastAPI vs gRPC-only) for `*-engine` services — deferred
  to Phase 2 when the first engine is implemented.

These are called out explicitly so they are not silently decided by whichever engineer
touches that code first.
