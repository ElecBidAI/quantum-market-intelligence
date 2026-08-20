# Deploying QMI to Render — free tier only

Deploys `render.yaml` as a [Render Blueprint](https://render.com/docs/blueprint-spec).
**Nothing in this file requires a card.** This was written and tested
against a real Render account this same session — a couple of things
failed on the first real attempt and got fixed in place; see the git
history on `render.yaml` and these `.github/workflows/` files for exactly
what broke and why, if that's useful context later.

## What's covered, and what isn't

| Piece | Where it runs | Cost |
| --- | --- | --- |
| `qmi-postgres` (Postgres) | Render, managed, free plan | $0 (1GB, **expires 30 days after creation** — see below) |
| `qmi-redis` (Redis-compatible) | Render, managed, free plan | $0 (in-memory only, lost on restart — fine, it's only a pub/sub relay) |
| `qmi-api` (Fastify gateway) | Render, free web service | $0 (spins down after ~15 min idle, wakes in a few seconds) |
| `qmi-web` (Next.js dashboard) | Render, free web service | $0 (same spin-down behavior) |
| `ai_council.run_pipeline` | GitHub Actions, scheduled | $0 (Render Cron Jobs have no free tier at all; this replaces that) |
| `backtester.research_runner` | GitHub Actions, scheduled | $0 (same) |
| `services/market-data` (exchange ingestion) | **Not deployed anywhere** | — |

**The one real gap**: `services/market-data` needs to run *continuously*
(a live Binance WebSocket connection), and Render has no free tier at all
for Background Workers — only Web Services, Key Value, and Postgres have
one. There's no genuinely free way to keep this specific piece running
24/7 on Render. For now, run it locally when you want fresh data flowing
into the deployed database (`DATABASE_URL` pointed at `qmi-postgres`'s
*external* connection string — see below), the same way this project has
been doing all along. Revisit paying for just this one service later if
continuous ingestion matters enough — it'd be the cheapest single line
item to add back (a Background Worker on Render's "starter" plan), not
the whole original four-service, ~$30+/month version.

**Why this is possible now**: `data/migrations/` no longer uses the
TimescaleDB extension. It only ever used it for hypertables (automatic
time-based partitioning) — real, but irrelevant at anything close to this
project's current data volume, and Render's free managed Postgres doesn't
support that extension. Removing it was a pure downgrade of "how this
scales at serious volume," not a functional change today.

## 1. Push to GitHub

```
git remote add origin <your-repo-url>
git push -u origin master
```

## 2. Apply the Blueprint

1. Sign up at [render.com](https://render.com) (free — no card at signup).
2. Dashboard -> **New** -> **Blueprint**.
3. Connect GitHub, select this repo. Render reads `render.yaml`
   automatically and proposes `qmi-postgres`, `qmi-redis`, `qmi-api`,
   `qmi-web`.
4. Give the Blueprint a name, review, **Deploy Blueprint**.

If a service fails to even get *created* (not just fail its build), check
that YAML block for a stray/incorrect field before assuming it's a code
problem — that happened twice this session (`fromService` needing a
`type` field; a `--` accidentally forwarded to `next start` by `pnpm run
... -- ...`, which pnpm doesn't need at all, unlike npm). A service stuck
on Render's generic "waking up" splash forever, rather than resolving,
usually means it was never actually built/deployed — check its **Deploys**
tab for "This service doesn't have any deploys yet" before assuming it's
just cold-starting.

## 3. Apply the database schema

Render's managed Postgres starts empty — nothing runs the migrations for
you automatically. From your own machine (with this repo's Python deps
installed, same as local dev):

1. Render dashboard -> `qmi-postgres` -> **Connect** -> copy the
   **External Database URL** (not the internal one — your machine isn't
   on Render's private network).
2. Run:
   ```
   DATABASE_URL="<external URL>" python data/apply_migrations.py
   ```
   This applies every file in `data/migrations/` in order and records each
   one in a `schema_migrations` table it creates — safe to re-run later
   for a newly-added migration too, since it skips whatever's already
   recorded there (several individual migration files are *not*
   idempotent on their own — e.g. a plain `RENAME COLUMN` — so this
   tracking is what actually makes re-running safe, not the migrations
   themselves).

## 4. Set the GitHub Actions secret

`.github/workflows/run-pipeline.yml` and `research-runner.yml` both need
a repo secret:

1. GitHub repo -> **Settings** -> **Secrets and variables** -> **Actions**
   -> **New repository secret**.
2. Name: `DATABASE_URL`. Value: the same *external* connection string from
   step 3 (GitHub's runners aren't on Render's private network either).

Both workflows also have `workflow_dispatch:` enabled — trigger them
manually once from the repo's **Actions** tab rather than waiting for
their schedule, to confirm they work before relying on the cron trigger.

## 5. Verify

- `https://qmi-api.onrender.com/health` -> `{"status":"ok",...}`.
- `https://qmi-web.onrender.com` loads, and registering an account works
  end to end (this needs step 3 done first — without it, `qmi-api` boots
  fine but doesn't register the DB-backed routes at all, and registration
  fails with a generic error, not a crash).
- Run `services/market-data` locally against the deployed database
  (`DATABASE_URL` = the external Postgres URL, `REDIS_URL` = `qmi-redis`'s
  external connection string from its own **Connect** tab) to get real
  bars flowing, then manually trigger both GitHub Actions workflows once.

**Data-volume reality carries over from local dev**: the regime
classifier needs 50+ real 1-minute bars before it can produce anything,
so `research_runner` won't have a meaningful backtest until
`services/market-data` has been feeding it for a while. Not a deployment
bug — see `services/backtester/src/backtester/research_runner.py`'s
module docstring.

## The 30-day free Postgres expiry

Render's free Postgres plan is deleted 30 days after creation, full stop
— there's no free renewal. Before that happens: either upgrade
`qmi-postgres` to a paid plan in Render's dashboard (a few dollars/month,
much cheaper than the four-service version this replaced), or export the
data (`pg_dump` against the external URL) and recreate the database +
re-run `data/apply_migrations.py` + re-run `pg_dump`'s output against the
new instance. Set a reminder — Render does not warn you before deleting
it.
