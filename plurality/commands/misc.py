"""Miscellaneous commands — import/export, stats, invite."""

from __future__ import annotations

import json

import discord
from discord import app_commands
from discord.ext import commands

from plurality import __version__
from plurality.commands.base import PluralityCog
from plurality.utils.errors import PluralityError, SyntaxError


class MiscCog(PluralityCog):
    @commands.command(name="export")
    async def export_prefix(self, ctx: commands.Context):
        await self._export(ctx, ctx.author.id)

    @commands.command(name="import")
    async def import_prefix(self, ctx: commands.Context):
        if not ctx.message.attachments:
            raise SyntaxError("Attach a JSON export file to import. Compatible with PluralKit exports!")
        attachment = ctx.message.attachments[0]
        data = json.loads(await attachment.read())
        await self._import(ctx, ctx.author.id, data)

    @commands.command(name="stats", aliases=["statistics"])
    async def stats_prefix(self, ctx: commands.Context):
        await self._stats(ctx)

    @commands.command(name="invite")
    async def invite_prefix(self, ctx: commands.Context):
        await self._invite(ctx)

    @app_commands.command(name="export", description="Export your system data as JSON")
    async def export_slash(self, interaction: discord.Interaction):
        await self._export(interaction, interaction.user.id)

    @app_commands.command(name="stats", description="View Plurality statistics")
    async def stats_slash(self, interaction: discord.Interaction):
        await self._stats(interaction)

    async def _export(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            data = await self.db.export_system(system.id)
            content = json.dumps(data, indent=2)
            file = discord.File(
                filename=f"plurality-{system.hid}.json",
                fp=content.encode(),
            )
            await self._respond(
                ctx,
                content="Here's your system export. Compatible with Plurality and PluralKit!",
                file=file,
                ephemeral=True,
            )
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _import(self, ctx, user_id: int, data: dict):
        try:
            system = await self.db.import_system_data(user_id, data)
            await self.send_success(
                ctx,
                f"Imported system `{system.hid}` with "
                f"{len(data.get('members', []))} members and "
                f"{len(data.get('groups', []))} groups.",
            )
        except PluralityError as e:
            await self.send_error(ctx, e)
        except json.JSONDecodeError:
            await self.send_error(ctx, SyntaxError("Invalid JSON file."))

    async def _stats(self, ctx):
        stats = await self.db.get_stats()
        embed = discord.Embed(
            title="Plurality Statistics",
            color=0x7B68EE,
        )
        embed.add_field(name="Systems", value=f"{stats['systems']:,}", inline=True)
        embed.add_field(name="Members", value=f"{stats['members']:,}", inline=True)
        embed.add_field(name="Proxied Messages", value=f"{stats['messages']:,}", inline=True)
        embed.add_field(name="Switches Logged", value=f"{stats['switches']:,}", inline=True)
        embed.add_field(name="Servers", value=f"{len(self.bot.guilds):,}", inline=True)
        embed.set_footer(text=f"Plurality v{__version__}")
        await self._respond(ctx, embed=embed)

    async def _invite(self, ctx):
        invite_url = getattr(self.bot, "invite_url", None)
        if invite_url:
            await self._respond(ctx, content=f"Invite Plurality: {invite_url}")
        else:
            permissions = discord.Permissions(
                send_messages=True,
                manage_messages=True,
                manage_webhooks=True,
                read_message_history=True,
                embed_links=True,
                attach_files=True,
                use_external_emojis=True,
            )
            url = discord.utils.oauth_url(self.bot.user.id, permissions=permissions)
            await self._respond(ctx, content=f"Invite Plurality to your server: {url}")

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCog(bot))