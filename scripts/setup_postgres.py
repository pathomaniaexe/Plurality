#!/usr/bin/env python3
"""Create the Plurality PostgreSQL database and run migrations."""

from __future__ import annotations

import argparse
import asyncio
import sys


async def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Plurality PostgreSQL database")
    parser.add_argument(
        "--admin-dsn",
        default="postgresql://postgres:postgres@localhost:5432/postgres",
        help="Connection string to the admin database (usually 'postgres')",
    )
    parser.add_argument(
        "--db-name",
        default="plurality",
        help="Database name to create",
    )
    parser.add_argument(
        "--app-dsn",
        default=None,
        help="App connection string (default: admin dsn with db name swapped)",
    )
    args = parser.parse_args()

    try:
        import asyncpg
    except ImportError:
        print("asyncpg not installed. Run: pip install asyncpg", file=sys.stderr)
        return 1

    app_dsn = args.app_dsn
    if not app_dsn:
        base = args.admin_dsn.rsplit("/", 1)[0]
        app_dsn = f"{base}/{args.db_name}"

    print(f"Connecting to admin DB...")
    try:
        conn = await asyncpg.connect(args.admin_dsn, timeout=5)
    except Exception as e:
        print(f"Could not connect to PostgreSQL: {e}", file=sys.stderr)
        print("\nMake sure PostgreSQL is running. In VS Code:", file=sys.stderr)
        print("  1. Open the PostgreSQL extension", file=sys.stderr)
        print("  2. Start/connect to your local server", file=sys.stderr)
        print("  3. Re-run this script with --admin-dsn matching your credentials", file=sys.stderr)
        return 1

    exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", args.db_name)
    if not exists:
        await conn.execute(f'CREATE DATABASE "{args.db_name}"')
        print(f"Created database '{args.db_name}'")
    else:
        print(f"Database '{args.db_name}' already exists")

    await conn.close()

    print(f"Running migrations on {app_dsn}...")
    from plurality.db.database import Database

    db = Database(app_dsn)
    await db.connect()
    stats = await db.get_stats()
    await db.close()
    print(f"Schema ready. Stats: {stats}")
    print(f"\nSet this in plurality.toml:\n  url = \"{app_dsn}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))