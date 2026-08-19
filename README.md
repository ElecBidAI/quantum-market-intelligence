# QMI — Quantum Market Intelligence

Crypto-first, multi-asset-ready quantitative market intelligence platform.

> **Core rule:** no AI agent, signal, strategy, or model may bypass the Risk Engine.
> See [`docs/risk/RISK-GOVERNANCE.md`](docs/risk/RISK-GOVERNANCE.md).

This repository is through **Phase 5 (Simulation Engine)**. There is still no
strategy-engine and no execution capability — `services/risk-engine`'s
`evaluate()` (the APPROVE/REDUCE/REJECT gate), `services/backtester`'s
event-driven engine, and `services/simulation-engine`'s Monte Carlo/stress
testing are all implemented and fully tested, but nothing calls them yet in a
live pipeline because nothing produces real strategy candidates yet. See
[`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](docs/architecture/QMI-MASTER-ARCHITECTURE.md)
for the full plan and what exists today. Live market data is real (Binance spot,
BTC/ETH) but read-only: nothing in this repository can place an order.

## Repository layout

See [`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](docs/architecture/QMI-MASTER-ARCHITECTURE.md#3-monorepo-layout).
Every directory under `services/`, `research/`, and `tests/` that isn't implemented
yet contains a `README.md` explaining what it will hold and which phase implements it.

## Prerequisites

- Node.js >= 20, [pnpm](https://pnpm.io/) (see `packageManager` in `package.json`)
- Python >= 3.11
- Docker (for local Postgres/TimescaleDB + Redis)

## Getting started

```bash
cp .env.example .env        # fill in local values; never commit .env

docker compose up -d        # Postgres/TimescaleDB + Redis
# apply data/migrations/*.sql in order (0001-0005) against $DATABASE_URL
# (docker-compose.yml also auto-applies them for a fresh volume)

pnpm install                 # installs apps/*, packages/contracts, packages/config,
                              # packages/observability, services/market-data

pip install -e "packages/quant-core[dev]" \
            -e "services/feature-engine[dev]" \
            -e "services/risk-engine[dev]" \
            -e "services/backtester[dev]" \
            -e "services/simulation-engine[dev]"

pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Run the Python tests separately (`--import-mode=importlib` avoids a module-name
collision between two packages that both have a `tests/test_engine.py`):

```bash
pytest --import-mode=importlib packages/quant-core/tests services/feature-engine/tests \
       services/risk-engine/tests services/backtester/tests services/simulation-engine/tests
```

## Running the live stack locally

```bash
pnpm --filter @qmi/market-data dev   # connects to Binance, ingests BTC/ETH
pnpm --filter @qmi/api dev           # exposes /health, /market/latest, /stream/market
pnpm --filter @qmi/web dev           # dashboard at http://localhost:3000

# once a few minutes of 1m bars have accumulated:
DATABASE_URL=$DATABASE_URL python -m feature_engine.main
```

```bash
curl http://localhost:4000/health
curl http://localhost:4000/market/latest?symbols=BTC-USDT,ETH-USDT
curl -N http://localhost:4000/stream/market?symbols=BTC-USDT   # live SSE feed
```

`apps/api` still boots with only `/health` if `DATABASE_URL`/`REDIS_URL` aren't set —
`/market/latest` and `/stream/market` are registered only when both are configured.

## Documentation

- [`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](docs/architecture/QMI-MASTER-ARCHITECTURE.md) — target architecture, stack, phases.
- [`docs/architecture/DATA-CONTRACTS.md`](docs/architecture/DATA-CONTRACTS.md) — canonical data shapes (source of truth: `packages/contracts`).
- [`docs/risk/RISK-GOVERNANCE.md`](docs/risk/RISK-GOVERNANCE.md) — binding risk policy, enforced starting Phase 3.
- [`services/market-data/README.md`](services/market-data/README.md) — what the Binance adapter does and doesn't ingest yet.
- [`services/feature-engine/README.md`](services/feature-engine/README.md) — how OHLCV becomes a feature vector, and what's deferred.
- [`services/risk-engine/README.md`](services/risk-engine/README.md) — the APPROVE/REDUCE/REJECT gate: what it checks, what's deferred, why it isn't wired into a pipeline yet.
- [`services/backtester/README.md`](services/backtester/README.md) — the event-driven backtest engine, its no-look-ahead guarantee, and what's deferred.
- [`services/simulation-engine/README.md`](services/simulation-engine/README.md) — trade-sequence Monte Carlo and stress testing, and which stress scenarios are deferred.

## Non-goals (see the implementation brief, Section 24)

No profitability promises, no auto-trading of real capital, no invented market data,
no live-money execution — paper trading only until Phase 10, which requires explicit
human approval.
