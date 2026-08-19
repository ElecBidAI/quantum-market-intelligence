# QMI — Quantum Market Intelligence

Crypto-first, multi-asset-ready quantitative market intelligence platform.

> **Core rule:** no AI agent, signal, strategy, or model may bypass the Risk Engine.
> See [`docs/risk/RISK-GOVERNANCE.md`](docs/risk/RISK-GOVERNANCE.md).

This repository is in **Phase 0 (Foundation)**. There is no live market data
ingestion, no strategies, no risk engine, and no execution capability yet — see
[`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](docs/architecture/QMI-MASTER-ARCHITECTURE.md)
for the full plan and what exists today.

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

pnpm install                 # installs apps/*, packages/contracts, packages/config,
                              # packages/observability

pip install -e "packages/quant-core[dev]"

pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Run the quant-core Python tests separately:

```bash
pytest packages/quant-core/tests
```

Run the API locally (health check only in Phase 0):

```bash
pnpm --filter @qmi/api dev
curl http://localhost:4000/health
```

Run the web placeholder locally:

```bash
pnpm --filter @qmi/web dev
```

## Documentation

- [`docs/architecture/QMI-MASTER-ARCHITECTURE.md`](docs/architecture/QMI-MASTER-ARCHITECTURE.md) — target architecture, stack, phases.
- [`docs/architecture/DATA-CONTRACTS.md`](docs/architecture/DATA-CONTRACTS.md) — canonical data shapes (source of truth: `packages/contracts`).
- [`docs/risk/RISK-GOVERNANCE.md`](docs/risk/RISK-GOVERNANCE.md) — binding risk policy, enforced starting Phase 3.

## Non-goals (see the implementation brief, Section 24)

No profitability promises, no auto-trading of real capital, no invented market data,
no live-money execution — paper trading only until Phase 10, which requires explicit
human approval.
