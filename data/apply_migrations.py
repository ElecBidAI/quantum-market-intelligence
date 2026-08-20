"""Applies every not-yet-applied data/migrations/*.sql file, in order,
against DATABASE_URL.

Needed because Render's managed Postgres (unlike the local
docker-compose.yml setup, which mounts data/migrations/ as
docker-entrypoint-initdb.d) has no built-in way to run init scripts — this
is the equivalent for that target.

Tracks applied filenames in a `schema_migrations` table rather than
assuming every migration is safe to re-run: several aren't (e.g.
0010_council_narratives_i18n.sql does a plain `RENAME COLUMN`, which
fails outright on a second run) — discovered by actually running this
script twice against a real database, not assumed.

Usage: DATABASE_URL=postgresql://... python data/apply_migrations.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
    if not migration_files:
        raise SystemExit(f"no .sql files found in {MIGRATIONS_DIR}")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    filename    TEXT PRIMARY KEY,
                    applied_at  TIMESTAMPTZ NOT NULL DEFAULT now()
                )
                """
            )
        conn.commit()

        applied_count = 0
        for path in migration_files:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM schema_migrations WHERE filename = %s", (path.name,)
                )
                already_applied = cursor.fetchone() is not None
            if already_applied:
                print(f"[apply_migrations] {path.name} already applied, skipping", file=sys.stderr)
                continue

            print(f"[apply_migrations] applying {path.name}...", file=sys.stderr)
            with conn.cursor() as cursor:
                cursor.execute(path.read_text())
                cursor.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (path.name,)
                )
            conn.commit()
            applied_count += 1

    print(f"[apply_migrations] applied {applied_count} new migration(s)", file=sys.stderr)


if __name__ == "__main__":
    main()
