"""Shared command utilities."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from plurality.constants import ERROR_EMOJI, SUCCESS_EMOJI
from plurality.db.database import Database
from plurality.db.models import Member, System
from plurality.utils.errors import NoSystemError, PluralityError


class PluralityCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db: Database = bot.db  # type: ignore[attr-defined]

    async def get_own_system(self, user_id: int) -> System:
        system = await self.db.get_system_by_account(user_id)
        if not system:
            raise NoSystemError()
        return system

    async def member_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        system = await self.db.get_system_by_account(interaction.user.id)
        if not system:
            return []
        members = await self.db.get_members(
            system.id, interaction.guild.id if interaction.guild else None
        )
        current_lower = current.lower()
        choices = []
        for m in members:
            label = m.display_name or m.name
            if current_lower in label.lower() or current_lower in m.name.lower():
                choices.append(app_commands.Choice(name=f"{label} ({m.hid})", value=m.name))
                if len(choices) >= 25:
                    break
        return choices

    async def send_error(self, ctx: commands.Context | discord.Interaction, error: PluralityError):
        msg = f"{ERROR_EMOJI} {error.message}"
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg, delete_after=15)

    async def send_success(self, ctx: commands.Context | discord.Interaction, message: str):
        msg = f"{SUCCESS_EMOJI} {message}"
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(msg, ephemeral=True)
            else:
                await ctx.response.send_message(msg, ephemeral=True)
        else:
            await ctx.send(msg)