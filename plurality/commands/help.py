"""Help and information commands."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from plurality import __version__
from plurality.commands.base import PluralityCog


class HelpCog(PluralityCog):
    @commands.command(name="help", aliases=["h", "commands"])
    async def help_prefix(self, ctx: commands.Context, *, topic: str = None):
        await self._show_help(ctx, topic)

    @app_commands.command(name="help", description="Show Plurality help")
    @app_commands.describe(topic="Optional topic: proxy, system, member, switch, autoproxy")
    async def help_slash(self, interaction: discord.Interaction, topic: Optional[str] = None):
        await self._show_help(interaction, topic)

    @commands.command(name="explain")
    async def explain_prefix(self, ctx: commands.Context):
        await self._explain(ctx)

    @app_commands.command(name="explain", description="Explain DID/OSDD and proxying")
    async def explain_slash(self, interaction: discord.Interaction):
        await self._explain(interaction)

    async def _show_help(self, ctx, topic: str | None):
        topics = {
            "proxy": (
                "**Proxying**\n"
                "Send a message with proxy tags and Plurality replaces it with your member's name.\n\n"
                "• `pl!member proxy <name> add [text]` — set tags\n"
                "• Type `[hello]` in chat — proxies as that member\n"
                "• Prefix `\\` to skip autoproxy\n"
                "• `/setup` — interactive wizard"
            ),
            "system": (
                "**System Commands**\n"
                "• `pl!system new [name]` — create your system\n"
                "• `pl!system` — view system info\n"
                "• `pl!system list` — list members\n"
                "• `pl!system proxy on/off` — toggle proxying per server\n"
                "• `/system` — slash command versions"
            ),
            "member": (
                "**Member Commands**\n"
                "• `pl!member new <name>` — add a member\n"
                "• `pl!member <name>` — view member info\n"
                "• `pl!member proxy <name> add [text]` — proxy tags\n"
                "• `pl!member pronouns <name> <pronouns>`\n"
                "• `/member` — slash commands with autocomplete"
            ),
            "switch": (
                "**Switch Commands**\n"
                "• `pl!switch <member>` — log a switch\n"
                "• `pl!switch out` — log switching out\n"
                "• `pl!system fronter` — who's fronting\n"
                "• `/switch history` — view history"
            ),
            "autoproxy": (
                "**Autoproxy**\n"
                "• `pl!autoproxy off` — disable\n"
                "• `pl!autoproxy front` — proxy as current fronter\n"
                "• `pl!autoproxy latch` — proxy as last-proxied member\n"
                "• `pl!autoproxy member <name>` — proxy as specific member"
            ),
        }

        if topic and topic.lower() in topics:
            embed = discord.Embed(
                title=f"Plurality Help — {topic.title()}",
                description=topics[topic.lower()],
                color=0x7B68EE,
            )
        else:
            embed = discord.Embed(
                title="Plurality — Help",
                description=(
                    "The best DID/OSDD proxy bot for Discord.\n\n"
                    "**Prefix:** `pl!` or `plurality!`\n"
                    "**Slash commands:** `/system`, `/member`, `/switch`, `/autoproxy`, `/setup`\n\n"
                    f"Use `pl!help <topic>` for details. Topics: {', '.join(topics.keys())}\n\n"
                    "**Why Plurality?**\n"
                    "• Slash commands + autocomplete\n"
                    "• Interactive setup wizard\n"
                    "• Zero-config SQLite database\n"
                    "• PluralKit import/export compatible\n"
                    "• Thread support\n"
                    "• Message edit/delete sync"
                ),
                color=0x7B68EE,
            )
            embed.set_footer(text=f"Plurality v{__version__}")
        await self._respond(ctx, embed=embed)

    async def _explain(self, ctx):
        embed = discord.Embed(
            title="About DID/OSDD & Proxying",
            description=(
                "**DID** (Dissociative Identity Disorder) and **OSDD-1** (Otherwise Specified "
                "Dissociative Disorder, Type 1) are conditions where a person has multiple "
                "distinct identities or personality states.\n\n"
                "A **system** is a group of these identities, called **members** or **alters**. "
                "The member currently in control is the **fronter**.\n\n"
                "**Proxying** lets members send messages under their own name and avatar in Discord, "
                "without needing separate accounts. You type a message with proxy tags (like `[hello]`) "
                "and Plurality replaces it with a webhook message from that member.\n\n"
                "Plurality is made with love for the plural community. 💜"
            ),
            color=0x7B68EE,
        )
        await self._respond(ctx, embed=embed)

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(HelpCog(bot))