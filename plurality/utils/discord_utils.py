"""Discord utility helpers."""

from __future__ import annotations

import re

import discord

from plurality.constants import MAX_MESSAGE_LENGTH

MENTION_PATTERN = re.compile(
    r"^<@!?(?P<id>\d{17,20})>\s*",
    re.UNICODE,
)

CLYDE_PATTERN = re.compile(r"clyde", re.IGNORECASE)
URL_PATTERN = re.compile(
    r"https?://[^\s<>]+",
    re.IGNORECASE,
)


def extract_leading_mention(content: str) -> tuple[str | None, str]:
    match = MENTION_PATTERN.match(content)
    if not match:
        return None, content
    return match.group(0).strip(), content[match.end():]


def fix_clyde(name: str) -> str:
    """Avoid Discord's Clyde filter by inserting a hair space."""
    match = CLYDE_PATTERN.search(name)
    if not match:
        return name
    idx = match.start() + 1
    return name[:idx] + "\u200a" + name[idx:]


def truncate_content(content: str, limit: int = MAX_MESSAGE_LENGTH) -> str:
    if len(content) <= limit:
        return content
    return content[: limit - 3] + "..."


def break_link_embeds(content: str) -> str:
    """Prevent embeds by wrapping URLs in angle brackets without protocol."""
    def replacer(m: re.Match[str]) -> str:
        url = m.group(0)
        broken = url.replace("://", "://\u200b")
        return f"<{broken}>"
    return URL_PATTERN.sub(replacer, content)


def member_name_for(member, ctx: str = "public") -> str:
    from plurality.utils.privacy import LookupContext, get_privacy_value

    lookup = LookupContext.OWNER if ctx == "owner" else LookupContext.PUBLIC
    display = member.display_name or member.name
    return get_privacy_value(member.name_privacy, lookup, display, member.name) or member.name


def check_bot_permissions(channel: discord.abc.GuildChannel) -> str | None:
    if not isinstance(channel, discord.abc.Messageable):
        return "This channel doesn't support messages."
    if not hasattr(channel, "guild") or channel.guild is None:
        return None
    me = channel.guild.me
    if me is None:
        return "Bot member not found in guild."
    perms = channel.permissions_for(me)
    if not perms.send_messages:
        return "I don't have permission to send messages here."
    if not perms.manage_webhooks:
        return "I need the **Manage Webhooks** permission to proxy messages."
    if not perms.manage_messages:
        return "I need the **Manage Messages** permission to proxy messages."
    return None