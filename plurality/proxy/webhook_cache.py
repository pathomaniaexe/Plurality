"""Webhook caching per channel."""

from __future__ import annotations

import logging

import discord

from plurality.db.database import Database

logger = logging.getLogger(__name__)

WEBHOOK_NAME = "Plurality Proxy"


class WebhookCache:
    def __init__(self, db: Database, bot: discord.Client):
        self.db = db
        self.bot = bot
        self._memory: dict[int, discord.Webhook] = {}

    async def get_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        if channel.id in self._memory:
            return self._memory[channel.id]

        cached = await self.db.get_webhook(channel.id)
        if cached:
            try:
                webhook = await self.bot.fetch_webhook(cached["webhook"])
                self._memory[channel.id] = webhook
                return webhook
            except (discord.NotFound, discord.HTTPException):
                await self.db.delete_webhook(channel.id)

        return await self._create_webhook(channel)

    async def _create_webhook(self, channel: discord.TextChannel) -> discord.Webhook:
        webhooks = await channel.webhooks()
        for wh in webhooks:
            if wh.name == WEBHOOK_NAME and wh.user and wh.user.id == channel.guild.me.id:
                await self.db.save_webhook(channel.id, wh.id, wh.token or "")
                self._memory[channel.id] = wh
                return wh

        webhook = await channel.create_webhook(name=WEBHOOK_NAME, reason="Plurality proxy webhook")
        await self.db.save_webhook(channel.id, webhook.id, webhook.token or "")
        self._memory[channel.id] = webhook
        return webhook

    async def invalidate(self, channel: discord.TextChannel) -> discord.Webhook:
        self._memory.pop(channel.id, None)
        await self.db.delete_webhook(channel.id)
        return await self._create_webhook(channel)