"""Message event handlers for proxying."""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

from plurality.constants import ERROR_EMOJI
from plurality.db.database import Database
from plurality.proxy.service import ProxyService
from plurality.utils.errors import PluralityError

logger = logging.getLogger(__name__)


class MessageHandler(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db  # type: ignore[attr-defined]
        self.proxy: ProxyService = bot.proxy  # type: ignore[attr-defined]
        self._last_messages: dict[int, int] = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.id == self.bot.user.id:
            return
        if message.guild is None:
            return

        self._last_messages[message.channel.id] = message.id

        ctx = await self.db.get_message_context(
            message.author.id, message.guild.id, message.channel.id
        )

        if message.content and await self._is_command(message):
            return

        try:
            await self.proxy.handle_message(message, ctx, allow_autoproxy=True)
        except PluralityError as e:
            if message.channel.permissions_for(message.guild.me).send_messages:
                await message.channel.send(f"{ERROR_EMOJI} {e.message}", delete_after=15)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or after.guild is None:
            return
        if self._last_messages.get(after.channel.id) != after.id:
            return

        ctx = await self.db.get_message_context(
            after.author.id, after.guild.id, after.channel.id
        )
        try:
            await self.proxy.handle_message(after, ctx, allow_autoproxy=False)
        except PluralityError as e:
            if after.channel.permissions_for(after.guild.me).send_messages:
                await after.channel.send(f"{ERROR_EMOJI} {e.message}", delete_after=15)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.guild is None:
            return
        await self.proxy.sync_delete(message)

    async def _is_command(self, message: discord.Message) -> bool:
        """Detect prefix/mention commands so we skip proxying.

        Do NOT call process_commands here — discord.py's built-in on_message
        already does that, and calling it twice causes duplicate responses.
        """
        content = message.content
        if not content:
            return False

        prefixes = getattr(self.bot, "prefixes", ("pl!",))
        for prefix in prefixes:
            if content.lower().startswith(prefix.lower()):
                return True

        if self.bot.user and content.startswith(f"<@{self.bot.user.id}>"):
            return True
        if self.bot.user and content.startswith(f"<@!{self.bot.user.id}>"):
            return True

        return False


async def setup(bot: commands.Bot):
    await bot.add_cog(MessageHandler(bot))