# feature-engine

Phase 2: implemented as a batch job, not a live service.

Reads the most recent closed OHLCV bars for the Phase 1 universe (BTC-USDT,
ETH-USDT, interval `1m`) from Postgres, computes a feature vector using
`packages/quant-core` (returns, descriptive stats, volatility, technical
indicators), and upserts it into the `features` table
(`data/migrations/0003_features.sql`).

The feature set is named and versioned (`feature_set = "phase2-v1"`,
`src/feature_engine/features.py`) so a later, incompatible feature set can be
added without silently reinterpreting rows already written. Any feature that
needs more history than is available is written as `null`, never computed
from a shorter, nonstandard window.

## Not in Phase 2

- Not a live/streaming service — `src/feature_engine/main.py` is a one-shot
  batch job meant to run on a schedule (cron, systemd timer, ...). It becomes
  event-driven once a real-time consumer (e.g. strategy-engine) needs that.
- Cross-asset features (e.g. BTC/ETH correlation) — deferred until a
  pairs/cross-asset strategy actually needs them.
- `services/statistical-engine` and `services/microstructure-engine` remain
  unimplemented as separate services; the statistics and correlation
  formulas they were expected to own live in `packages/quant-core` instead,
  consumed directly here. They become their own services only if a reason
  emerges to run them independently of feature-engine (e.g. a different
  latency/scaling profile).

## Running locally

```bash
pip install -e "packages/quant-core[dev]" -e "services/feature-engine[dev]"
DATABASE_URL=postgres://qmi:qmi_dev_password@localhost:5432/qmi \
  python -m feature_engine.main
```

quant-core is not declared as a formal `pyproject.toml` dependency here —
Python has no first-class monorepo path-dependency mechanism the way pnpm
workspaces do, so both packages are installed editable into the same
environment instead (see the command above and `.github/workflows/ci.yml`).

## Tests

`tests/test_features.py` (pure `compute_features` logic against synthetic
bars of varying length), `tests/test_db.py` (SQL shape and row-mapping
against a fake cursor — no real Postgres in tests).
