"""Mental health support commands."""

from __future__ import annotations

import discord
from discord.ext import commands

from plurality.commands.base import PluralityCog


class MentalHealthCog(PluralityCog):
    @commands.command(name="grounding", aliases=["ground"])
    async def grounding(self, ctx: commands.Context):
        embed = discord.Embed(
            title="5-4-3-2-1 Grounding Exercise",
            description=(
                "Take a moment. Breathe slowly.\n\n"
                "**5** things you can **see**\n"
                "**4** things you can **touch**\n"
                "**3** things you can **hear**\n"
                "**2** things you can **smell**\n"
                "**1** thing you can **taste**\n\n"
                "You're here. You're safe. This moment will pass."
            ),
            color=0x7B68EE,
        )
        await ctx.send(embed=embed)

    @commands.command(name="breathing", aliases=["attack", "panic"])
    async def breathing(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Breathing Exercise",
            description=(
                "Try box breathing:\n\n"
                "🟦 **Breathe in** for 4 seconds\n"
                "⏸️ **Hold** for 4 seconds\n"
                "🟩 **Breathe out** for 4 seconds\n"
                "⏸️ **Hold** for 4 seconds\n\n"
                "Repeat 4 times. You've got this."
            ),
            color=0x7B68EE,
        )
        await ctx.send(embed=embed)

    @commands.command(name="hotlines", aliases=["hotline", "crisis"])
    async def hotlines(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Crisis Resources",
            description=(
                "**988** — Suicide & Crisis Lifeline (US)\n"
                "**741741** — Crisis Text Line (text HOME)\n"
                "**1-800-273-8255** — National Suicide Prevention Lifeline\n"
                "**translifeline.org** — Trans Lifeline\n"
                "**thetrevorproject.org** — Trevor Project (LGBTQ+ youth)\n"
                "**international-suicide-prevention.org** — International resources\n\n"
                "You matter. Please reach out if you need help."
            ),
            color=0x7B68EE,
        )
        await ctx.send(embed=embed)

    @commands.command(name="loved")
    async def loved(self, ctx: commands.Context):
        await ctx.send(
            embed=discord.Embed(
                description="You are loved. You are valued. You deserve to be here. 💜",
                color=0x7B68EE,
            )
        )

    @commands.command(name="resources", aliases=["res", "mh"])
    async def resources(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Mental Health Resources",
            description=(
                "• `pl!grounding` — 5-4-3-2-1 grounding exercise\n"
                "• `pl!breathing` — box breathing for panic attacks\n"
                "• `pl!hotlines` — crisis hotlines\n"
                "• `pl!loved` — a reminder that you matter\n"
                "• `pl!explain` — learn about DID/OSDD and proxying"
            ),
            color=0x7B68EE,
        )
        await ctx.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(MentalHealthCog(bot))