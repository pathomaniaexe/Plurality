"""Configuration loading from environment and optional TOML file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass
class Config:
    token: str
    database_url: str = "sqlite+aiosqlite:///plurality.db"
    prefixes: tuple[str, ...] = ("pl!", "plurality!")
    owner_ids: frozenset[int] = field(default_factory=frozenset)
    support_server: str | None = None
    invite_url: str | None = None
    log_level: str = "INFO"

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> Config:
        data: dict = {}
        path = Path(config_path or os.getenv("PLURALITY_CONFIG", "plurality.toml"))
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)

        bot = data.get("bot", {})
        db = data.get("database", {})

        token = (os.getenv("DISCORD_TOKEN") or bot.get("token", "")).strip()
        if token.lower().startswith("bot "):
            token = token[4:].strip()
        if not token:
            raise ValueError(
                "Discord bot token required. Set DISCORD_TOKEN env var or bot.token in plurality.toml"
            )
        placeholders = {
            "your_bot_token_here",
            "bot_token_goes_here",
            "your_token_here",
            "insert_token_here",
        }
        if token.lower() in placeholders or token.startswith("YOUR_"):
            raise ValueError(
                "plurality.toml still has the placeholder token. "
                "Get your real bot token from https://discord.com/developers/applications "
                "→ your app → Bot → Reset Token → copy it into plurality.toml"
            )
        if len(token) < 50 or "." not in token:
            raise ValueError(
                "The token in plurality.toml doesn't look like a valid Discord bot token. "
                "It should be a long string with letters, numbers, and dots. "
                "Copy it fresh from the Discord Developer Portal (Bot → Reset Token)."
            )

        database_url = (
            os.getenv("DATABASE_URL")
            or db.get("url")
            or db.get("connection_string")
            or "sqlite+aiosqlite:///plurality.db"
        )

        prefixes = tuple(bot.get("prefixes", ["pl!", "plurality!"]))
        owner_ids = frozenset(int(x) for x in bot.get("owner_ids", []))
        support_server = bot.get("support_server")
        invite_url = bot.get("invite_url")
        log_level = bot.get("log_level", os.getenv("LOG_LEVEL", "INFO"))

        return cls(
            token=token,
            database_url=database_url,
            prefixes=prefixes,
            owner_ids=owner_ids,
            support_server=support_server,
            invite_url=invite_url,
            log_level=log_level,
        )