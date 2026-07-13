"""Embed builders."""

from __future__ import annotations

import discord

from plurality.constants import EMBED_COLOR, PrivacyLevel
from plurality.db.models import Member, System
from plurality.utils.privacy import LookupContext, get_privacy_value, level_name


def base_embed(title: str | None = None, description: str | None = None) -> discord.Embed:
    embed = discord.Embed(color=EMBED_COLOR)
    if title:
        embed.title = title
    if description:
        embed.description = description
    return embed


def system_embed(system: System, ctx: LookupContext = LookupContext.PUBLIC) -> discord.Embed:
    name = system.name or f"Unnamed System ({system.hid})"
    embed = base_embed(title=name)
    embed.set_footer(text=f"ID: {system.hid}")

    desc = get_privacy_value(system.description_privacy, ctx, system.description)
    if desc:
        embed.description = desc
    if system.avatar_url:
        embed.set_thumbnail(url=system.avatar_url)
    if system.tag:
        embed.add_field(name="Tag", value=system.tag, inline=True)
    if system.color:
        embed.colour = discord.Colour(int(system.color, 16))
    return embed


def member_embed(member: Member, ctx: LookupContext = LookupContext.PUBLIC) -> discord.Embed:
    name = get_privacy_value(
        member.name_privacy, ctx, member.display_name or member.name, member.name
    )
    embed = base_embed(title=name or member.name)
    embed.set_footer(text=f"ID: {member.hid}")

    desc = get_privacy_value(member.description_privacy, ctx, member.description)
    if desc:
        embed.description = desc

    pronouns = get_privacy_value(member.pronoun_privacy, ctx, member.pronouns)
    if pronouns:
        embed.add_field(name="Pronouns", value=pronouns, inline=True)

    birthday = get_privacy_value(member.birthday_privacy, ctx, member.birthday)
    if birthday:
        embed.add_field(name="Birthday", value=birthday, inline=True)

    if member.proxy_tags:
        tags = ", ".join(
            f"`{t.prefix}text{t.suffix}`" if t.prefix or t.suffix else "`(empty)`"
            for t in member.proxy_tags[:5]
        )
        if len(member.proxy_tags) > 5:
            tags += f" (+{len(member.proxy_tags) - 5} more)"
        embed.add_field(name="Proxy Tags", value=tags, inline=False)

    avatar = get_privacy_value(member.avatar_privacy, ctx, member.avatar_url)
    if avatar:
        embed.set_thumbnail(url=avatar)

    if member.color:
        try:
            embed.colour = discord.Colour(int(member.color, 16))
        except ValueError:
            pass

    return embed


def privacy_field(name: str, level: PrivacyLevel) -> str:
    return f"**{name}**: {level_name(level)}"