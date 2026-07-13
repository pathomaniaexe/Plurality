"""Parse a SQLite database path from config."""

from __future__ import annotations


def parse_sqlite_path(url: str | None) -> str:
    """Return a filesystem path for the SQLite database.

    Accepts:
      - plain path: ``plurality.db``
      - SQLite URLs: ``sqlite:///plurality.db`` / ``sqlite+aiosqlite:///plurality.db``
    """
    if not url or not url.strip():
        return "plurality.db"

    url = url.strip()
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            path = url[len(prefix) :]
            return path or "plurality.db"

    if url.startswith(("postgresql://", "postgres://", "Host=", "host=")):
        raise ValueError(
            "PostgreSQL is no longer supported. "
            "Use SQLite instead (default: plurality.db), e.g. "
            "DATABASE_URL=sqlite+aiosqlite:///plurality.db"
        )

    # Treat bare paths as SQLite file paths
    return url
