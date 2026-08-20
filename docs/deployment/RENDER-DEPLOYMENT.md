# Deploying QMI to Render

Deploys every service in `render.yaml` as a
[Render Blueprint](https://render.com/docs/blueprint-spec). This was written
and reviewed against Render's current documented Blueprint schema, but has
not been applied against a real Render account — the first real deploy will
likely surface one or two things to fix. Treat this as a strong starting
point, not a guarantee.

## Why Postgres is self-hosted, not Render's managed product

Every migration in `data/migrations/` depends on the TimescaleDB extension
(`CREATE EXTENSION timescaledb`, `create_hypertable(...)` on `market_ticks`,
`ohlcv`, `orderbook_snapshots`, `features`, `funding_rates`,
`futures_basis`). Render's managed Postgres product doesn't support that
extension. `render.yaml` instead runs the exact same
`timescale/timescaledb:latest-pg16` image `docker-compose.yml` already uses
locally, as a private service (`qmi-postgres`) with its own persistent
disk — not reachable from the public internet, only from the other services
in this Blueprint.

## 1. Push to GitHub

Render deploys from a GitHub (or GitLab) repo. If this repo isn't pushed
yet:

```
git remote add origin <your-repo-url>
git push -u origin master
```

## 2. Create a Render account and apply the Blueprint

1. Sign up at [render.com](https://render.com) (free).
2. Dashboard -> **New** -> **Blueprint**.
3. Connect your GitHub account and select this repo. Render reads
   `render.yaml` from the repo root automatically.
4. Review the seven services it proposes (`qmi-postgres`, `qmi-redis`,
   `qmi-api`, `qmi-web`, `qmi-market-data`, `qmi-run-pipeline`,
   `qmi-research-runner`) and click **Apply**.

Every service on `plan: starter` costs money once Render's free trial
credit runs out (roughly $7/service/month at the time this was written —
confirm current pricing in Render's dashboard before applying). To spend
nothing: `qmi-api` and `qmi-web` can run on Render's free web-service tier
(it spins down after ~15 minutes idle and takes a few seconds to wake back
up on the next request — fine for occasionally checking the dashboard, not
for something you want always-on). `qmi-market-data` genuinely needs to
stay running continuously to ingest real bars, so it can't meaningfully run
on a tier that spins down.

## 3. Wire up DATABASE_URL manually

Because `qmi-postgres` is a self-hosted private service, Render has no
built-in way to hand its connection string to the other services (that
auto-wiring only exists for Render's own managed database products) — this
is the one manual step:

1. Open the `qmi-postgres` service in Render's dashboard. Note its internal
   hostname (shown on the service's **Connect** tab) and the
   auto-generated `POSTGRES_PASSWORD` value (under **Environment**).
2. Build the connection string:
   `postgresql://qmi:<password>@<qmi-postgres-internal-host>:5432/qmi`
3. Paste that exact value into `DATABASE_URL` for **each** of: `qmi-api`,
   `qmi-market-data`, `qmi-run-pipeline`, `qmi-research-runner` (their
   **Environment** tabs — `render.yaml` deliberately left these as
   `sync: false` placeholders for this reason).
4. Save. Render redeploys `qmi-api`/`qmi-market-data` automatically; for
   the two cron jobs, the new value takes effect on their next scheduled
   (or manually triggered) run.

## 4. Verify

- `qmi-postgres`'s **Logs** tab should show each `data/migrations/000N_*.sql`
  file being applied during its very first boot (the official Postgres
  image only runs `/docker-entrypoint-initdb.d` once, against an empty
  data directory — see `deploy/postgres/Dockerfile`'s comment).
- `https://qmi-api.onrender.com/health` should return
  `{"status":"ok",...}`.
- `https://qmi-web.onrender.com` should load, and registering an account
  should work end to end.
- `qmi-market-data`'s logs should show it connecting to Binance's public
  streams and writing bars.
- Manually trigger `qmi-run-pipeline` and `qmi-research-runner` once each
  from their dashboard pages rather than waiting for their schedules.

**Data-volume reality carries over from local dev**: `qmi-research-runner`
needs real accumulated OHLCV history to produce anything meaningful (the
regime classifier alone needs 50+ real 1-minute bars) — right after first
deploy, `qmi-market-data` needs to run for a while before the cron jobs
have anything real to work with. This is inherent to the design (see
`services/backtester/src/backtester/research_runner.py`'s module
docstring), not a deployment bug.

## Applying a new migration after the first deploy

`/docker-entrypoint-initdb.d` only runs on a truly empty data directory, so
a migration added *after* `qmi-postgres`'s first boot won't run
automatically. Open a **Shell** on any Python service in this Blueprint
(they already have `psycopg` installed) and run:

```python
python - <<'EOF'
import os, psycopg
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    with conn.cursor() as cur:
        cur.execute(open("data/migrations/00XX_new_migration.sql").read())
    conn.commit()
EOF
```
