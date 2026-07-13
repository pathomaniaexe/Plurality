"""SQLite database backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


def _normalize_row(row: Any) -> dict | None:
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    return dict(row)


class SqliteBackend:
    def __init__(self, path: str):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA journal_mode = WAL")

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def migrate(self) -> None:
        schema = (Path(__file__).parent / "schema.sql").read_text()
        await self._conn.executescript(schema)
        await self._conn.commit()

    async def fetchone(self, sql: str, params: tuple = ()) -> dict | None:
        async with self._conn.execute(sql, params) as cursor:
            row = await cursor.fetchone()
            return _normalize_row(row)

    async def fetchall(self, sql: str, params: tuple = ()) -> list[dict]:
        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [_normalize_row(r) for r in rows]

    async def execute(self, sql: str, params: tuple = ()) -> int:
        async with self._conn.execute(sql, params) as cursor:
            await self._conn.commit()
            return cursor.lastrowid or 0

    async def insert_returning_id(self, sql: str, params: tuple = ()) -> int:
        return await self.execute(sql, params)
