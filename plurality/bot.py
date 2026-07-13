"""Plurality Discord bot."""

from __future__ import annotations

import logging

import aiohttp
import discord
from discord.ext import commands

from plurality import __version__
from plurality.config import Config
from plurality.db.database import Database
from plurality.proxy.service import ProxyService

logger = logging.getLogger(__name__)

COGS = [
    "plurality.commands.system",
    "plurality.commands.member",
    "plurality.commands.switch",
    "plurality.commands.autoproxy",
    "plurality.commands.group",
    "plurality.commands.server",
    "plurality.commands.help",
    "plurality.commands.mental_health",
    "plurality.commands.misc",
    "plurality.handlers.messages",
]


class PluralityBot(commands.Bot):
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True

        super().__init__(
            command_prefix=self._prefix_callable(config.prefixes),
            intents=intents,
            help_command=None,
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="systems front | pl!help",
            ),
        )

        self.config = config
        self.prefixes = config.prefixes
        self.invite_url = config.invite_url
        self.db = Database(config.database_url)
        self._http_session: aiohttp.ClientSession | None = None
        self.proxy: ProxyService | None = None

    @staticmethod
    def _prefix_callable(prefixes: tuple[str, ...]):
        async def get_prefix(bot, message: discord.Message):
            return list(prefixes)
        return get_prefix

    async def setup_hook(self):
        self._http_session = aiohttp.ClientSession()
        self.proxy = ProxyService(self.db, self, self._http_session)

        for cog in COGS:
            await self.load_extension(cog)

        try:
            synced = await self.tree.sync()
            logger.info("Synced %d slash commands", len(synced))
        except Exception as e:
            logger.error("Failed to sync slash commands: %s", e)

    async def on_ready(self):
        logger.info(
            "Plurality v%s logged in as %s (%d guilds) [db: %s]",
            __version__,
            self.user,
            len(self.guilds),
            self.db.path,
        )

    async def close(self):
        await self.db.close()
        if self._http_session:
            await self._http_session.close()
        await super().close()


async def run_bot(config: Config | None = None):
    logging.basicConfig(
        level=getattr(logging, (config or Config.load()).log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cfg = config or Config.load()
    bot = PluralityBot(cfg)
    await bot.db.connect()

    try:
        await bot.start(cfg.token)
    finally:
        await bot.close()