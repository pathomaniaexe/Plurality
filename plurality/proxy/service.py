"""Core proxy execution service."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO

import aiohttp
import discord

from plurality.constants import (
    ERROR_EMOJI,
    MAX_ATTACHMENT_CHUNK_BYTES,
    MAX_PROXY_NAME_LENGTH,
)
from plurality.db.database import Database
from plurality.db.models import MessageContext, ProxyMatch
from plurality.proxy.matcher import ProxyMatcher
from plurality.proxy.webhook_cache import WebhookCache
from plurality.utils import discord_utils
from plurality.utils.errors import PluralityError, attachment_too_large, proxy_name_too_long, proxy_name_too_short

logger = logging.getLogger(__name__)


class ProxyService:
    def __init__(self, db: Database, bot: discord.Client, session: aiohttp.ClientSession | None = None):
        self.db = db
        self.bot = bot
        self.matcher = ProxyMatcher()
        self.webhooks = WebhookCache(db, bot)
        self._session = session

    async def handle_message(
        self,
        message: discord.Message,
        ctx: MessageContext,
        allow_autoproxy: bool = True,
    ) -> bool:
        if not self._should_proxy(message, ctx):
            return False

        members = await self.db.get_proxy_members(message.author.id, message.guild.id if message.guild else None)
        if not members:
            return False

        content = message.content or ""
        has_attachments = bool(message.attachments)

        match = self.matcher.try_match(ctx, members, content, has_attachments, allow_autoproxy)
        if not match:
            return False

        if not isinstance(message.channel, discord.TextChannel):
            return False

        perm_error = discord_utils.check_bot_permissions(message.channel)
        if perm_error:
            await message.channel.send(f"{ERROR_EMOJI} {perm_error}", delete_after=15)
            return False

        proxy_name = match.member.proxy_name(ctx.system_tag)
        if len(proxy_name) < 2:
            raise proxy_name_too_short(proxy_name)
        if len(proxy_name) > MAX_PROXY_NAME_LENGTH:
            raise proxy_name_too_long(proxy_name)

        sender_perms = message.channel.permissions_for(message.author)
        allow_everyone = sender_perms.mention_everyone
        allow_embeds = sender_perms.embed_links

        await self._execute_proxy(message, ctx, match, allow_everyone, allow_embeds)
        return True

    def _should_proxy(self, message: discord.Message, ctx: MessageContext) -> bool:
        if ctx.system_id is None:
            return False
        if message.author.bot or message.webhook_id:
            return False
        if not message.guild:
            return False
        if not ctx.proxy_enabled or ctx.in_blacklist:
            return False
        content = (message.content or "").strip()
        if not content and not message.attachments:
            return False
        return True

    async def _execute_proxy(
        self,
        trigger: discord.Message,
        ctx: MessageContext,
        match: ProxyMatch,
        allow_everyone: bool,
        allow_embeds: bool,
    ) -> None:
        channel = trigger.channel
        assert isinstance(channel, discord.TextChannel)

        content = match.content
        if match.member.keep_proxy and match.proxy_tags and not match.is_autoproxy:
            tag = match.proxy_tags
            content = f"{tag.prefix}{content}{tag.suffix}"

        if not allow_embeds:
            content = discord_utils.break_link_embeds(content)

        content = discord_utils.truncate_content(content)
        name = discord_utils.fix_clyde(match.member.proxy_name(ctx.system_tag))[:80]
        avatar = match.member.proxy_avatar() or ctx.system_avatar

        webhook = await self.webhooks.get_webhook(channel)

        try:
            sent = await self._send_webhook(
                webhook, name, avatar, content, trigger.attachments, allow_everyone
            )
        except discord.NotFound:
            webhook = await self.webhooks.invalidate(channel)
            sent = await self._send_webhook(
                webhook, name, avatar, content, trigger.attachments, allow_everyone
            )

        await asyncio.gather(
            self._delete_trigger(trigger),
            self.db.add_message(
                mid=sent.id,
                channel=channel.id,
                guild=channel.guild.id if channel.guild else None,
                member=match.member.id,
                sender=trigger.author.id,
                original_mid=trigger.id,
            ),
            self._log_proxy(channel, ctx, match, trigger, sent),
            return_exceptions=True,
        )

    async def _send_webhook(
        self,
        webhook: discord.Webhook,
        name: str,
        avatar: str | None,
        content: str,
        attachments: list[discord.Attachment],
        allow_everyone: bool,
    ) -> discord.Message:
        files = await self._download_attachments(attachments)
        chunks = self._chunk_files(files)

        allowed_mentions = discord.AllowedMentions(
            everyone=allow_everyone,
            roles=allow_everyone,
            users=True,
            replied_user=True,
        )

        if not chunks:
            return await webhook.send(
                content=content or None,
                username=name,
                avatar_url=avatar,
                allowed_mentions=allowed_mentions,
                wait=True,
            )

        first_files = [discord.File(BytesIO(data), filename=fn) for fn, data in chunks[0]]
        msg = await webhook.send(
            content=content or None,
            username=name,
            avatar_url=avatar,
            files=first_files,
            allowed_mentions=allowed_mentions,
            wait=True,
        )

        for chunk in chunks[1:]:
            extra_files = [discord.File(BytesIO(data), filename=fn) for fn, data in chunk]
            await webhook.send(username=name, avatar_url=avatar, files=extra_files, wait=True)

        return msg

    async def _download_attachments(
        self, attachments: list[discord.Attachment]
    ) -> list[tuple[str, bytes]]:
        if not attachments:
            return []

        session = self._session
        results: list[tuple[str, bytes]] = []

        for att in attachments:
            if att.size >= MAX_ATTACHMENT_CHUNK_BYTES:
                raise attachment_too_large()
            if session:
                async with session.get(att.url) as resp:
                    data = await resp.read()
            else:
                data = await att.read()
            results.append((att.filename, data))

        return results

    def _chunk_files(self, files: list[tuple[str, bytes]]) -> list[list[tuple[str, bytes]]]:
        if not files:
            return []

        chunks: list[list[tuple[str, bytes]]] = []
        current: list[tuple[str, bytes]] = []
        current_size = 0

        for filename, data in files:
            if len(data) >= MAX_ATTACHMENT_CHUNK_BYTES:
                raise attachment_too_large()
            if current_size + len(data) >= MAX_ATTACHMENT_CHUNK_BYTES and current:
                chunks.append(current)
                current = []
                current_size = 0
            current.append((filename, data))
            current_size += len(data)

        if current:
            chunks.append(current)
        return chunks

    async def _delete_trigger(self, message: discord.Message) -> None:
        await asyncio.sleep(0.01)
        try:
            await message.delete()
        except discord.NotFound:
            logger.warning("Trigger message %s already deleted", message.id)

    async def _log_proxy(
        self,
        channel: discord.TextChannel,
        ctx: MessageContext,
        match: ProxyMatch,
        trigger: discord.Message,
        sent: discord.Message,
    ) -> None:
        if not ctx.log_channel or ctx.in_log_blacklist:
            return
        log_channel = channel.guild.get_channel(ctx.log_channel)
        if not isinstance(log_channel, discord.TextChannel):
            return

        embed = discord.Embed(
            title="Proxied Message",
            description=sent.content or "(attachment only)",
            color=0x7B68EE,
        )
        embed.add_field(name="Member", value=match.member.name, inline=True)
        embed.add_field(name="Author", value=trigger.author.mention, inline=True)
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.set_footer(text=f"Message ID: {sent.id}")
        try:
            await log_channel.send(embed=embed)
        except discord.HTTPException:
            pass

    async def sync_edit(self, message: discord.Message, ctx: MessageContext) -> bool:
        """Re-proxy edited messages that were previously proxied."""
        record = await self.db.get_message(message.id)
        if record:
            return False

        members = await self.db.get_proxy_members(message.author.id, message.guild.id if message.guild else None)
        match = self.matcher.try_match(ctx, members, message.content or "", bool(message.attachments), False)
        if not match:
            return False

        return await self.handle_message(message, ctx, allow_autoproxy=False)

    async def sync_delete(self, message: discord.Message) -> None:
        """Delete proxied webhook message when original trigger is deleted."""
        record = await self.db.get_message(message.id)
        if not record:
            return

        channel = message.channel
        if not isinstance(channel, discord.TextChannel):
            return

        try:
            webhook = await self.bot.fetch_webhook(
                (await self.db.get_webhook(channel.id))["webhook"]
            )
            await webhook.delete_message(record["mid"])
        except (discord.NotFound, discord.HTTPException, TypeError, KeyError):
            pass
        await self.db.delete_message_record(message.id)