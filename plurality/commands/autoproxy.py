"""Autoproxy configuration commands."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from plurality.commands.base import PluralityCog
from plurality.constants import NOTE_EMOJI, AutoproxyMode
from plurality.utils.errors import PluralityError, SyntaxError, member_not_found


class AutoproxyCog(PluralityCog):
    @commands.command(name="autoproxy", aliases=["ap"])
    async def autoproxy_prefix(self, ctx: commands.Context, mode: str = None, *, member: str = None):
        await self._set_autoproxy(ctx, ctx.author.id, mode, member)

    @app_commands.command(name="autoproxy", description="Configure autoproxy for this server")
    @app_commands.describe(
        mode="off, front, latch, or member",
        member="Member name (required for member mode)",
    )
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Off", value="off"),
            app_commands.Choice(name="Front", value="front"),
            app_commands.Choice(name="Latch", value="latch"),
            app_commands.Choice(name="Member", value="member"),
        ]
    )
    @app_commands.autocomplete(member=PluralityCog.member_autocomplete)
    async def autoproxy_slash(
        self, interaction: discord.Interaction, mode: Optional[str] = None, member: Optional[str] = None
    ):
        await self._set_autoproxy(interaction, interaction.user.id, mode, member)

    async def _set_autoproxy(self, ctx, user_id: int, mode: str | None, member_name: str | None):
        try:
            system = await self.get_own_system(user_id)
            guild = ctx.guild if hasattr(ctx, "guild") else None
            if not guild:
                raise SyntaxError("Autoproxy must be configured in a server.")

            if mode is None:
                msg_ctx = await self.db.get_message_context(user_id, guild.id, 0)
                status = self._describe_mode(msg_ctx.autoproxy_mode, msg_ctx.autoproxy_member)
                await self._respond(ctx, content=f"{NOTE_EMOJI} Autoproxy is **{status}** in this server.")
                return

            mode = mode.lower()
            if mode in ("off", "stop", "disable", "no"):
                await self.db.upsert_system_guild(
                    system.id, guild.id, autoproxy_mode=AutoproxyMode.OFF, autoproxy_member=None
                )
                await self.send_success(ctx, "Autoproxy turned off in this server.")
            elif mode in ("front", "fronter", "switch"):
                await self.db.upsert_system_guild(
                    system.id, guild.id, autoproxy_mode=AutoproxyMode.FRONT, autoproxy_member=None
                )
                await self.send_success(
                    ctx,
                    "Autoproxy set to **front mode**. Messages will proxy as your current first fronter.",
                )
            elif mode in ("latch", "last", "sticky", "stick"):
                await self.db.upsert_system_guild(
                    system.id, guild.id, autoproxy_mode=AutoproxyMode.LATCH, autoproxy_member=None
                )
                await self.send_success(
                    ctx,
                    "Autoproxy set to **latch mode**. Messages will proxy as your last-proxied member.",
                )
            elif mode == "member":
                if not member_name:
                    raise SyntaxError("Member mode requires a member name. Example: `pl!autoproxy member Alice`")
                member = await self.db.find_member(system.id, member_name, guild.id)
                if not member:
                    raise member_not_found(member_name)
                await self.db.upsert_system_guild(
                    system.id, guild.id, autoproxy_mode=AutoproxyMode.MEMBER, autoproxy_member=member.id
                )
                await self.send_success(ctx, f"Autoproxy set to **{member.name}** in this server.")
            else:
                raise SyntaxError(
                    f"Unknown mode `{mode}`. Use: off, front, latch, or member."
                )
        except PluralityError as e:
            await self.send_error(ctx, e)

    def _describe_mode(self, mode: AutoproxyMode, member_id: int | None) -> str:
        if mode == AutoproxyMode.OFF:
            return "off"
        if mode == AutoproxyMode.FRONT:
            return "front (current fronter)"
        if mode == AutoproxyMode.LATCH:
            return "latch (last proxied)"
        if mode == AutoproxyMode.MEMBER:
            return f"member (ID: {member_id})"
        return "unknown"

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(AutoproxyCog(bot))