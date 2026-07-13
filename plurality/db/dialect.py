"""SQLite SQL helpers."""

from __future__ import annotations


def order_name(column: str) -> str:
    return f"{column} COLLATE NOCASE"


def insert_ignore(table: str, columns: str, placeholders: str) -> str:
    return f"INSERT OR IGNORE INTO {table} ({columns}) VALUES ({placeholders})"


def insert_replace(table: str, columns: str, placeholders: str) -> str:
    return f"INSERT OR REPLACE INTO {table} ({columns}) VALUES ({placeholders})"
