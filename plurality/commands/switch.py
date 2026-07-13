"""Switch tracking commands."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from plurality.commands.base import PluralityCog
from plurality.constants import NOTE_EMOJI
from plurality.utils.errors import PluralityError, SyntaxError, member_not_found


class SwitchCog(PluralityCog):
    switch_group = app_commands.Group(name="switch", description="Track switches")

    @commands.group(name="switch", aliases=["sw"], invoke_without_command=True)
    async def switch_prefix(self, ctx: commands.Context, *members: str):
        if ctx.invoked_subcommand is None:
            if members:
                await self._register_switch(ctx, ctx.author.id, list(members))
            else:
                await self._show_current(ctx, ctx.author.id)

    @switch_prefix.command(name="out")
    async def switch_out_prefix(self, ctx: commands.Context):
        await self._register_switch(ctx, ctx.author.id, [])

    @switch_prefix.command(name="delete")
    async def switch_delete_prefix(self, ctx: commands.Context, scope: str = None):
        await self._delete_switch(ctx, ctx.author.id, scope)

    @switch_group.command(name="register", description="Register a switch")
    @app_commands.describe(members="Member names to register as fronting (comma-separated)")
    async def switch_register_slash(self, interaction: discord.Interaction, members: str):
        names = [n.strip() for n in members.split(",") if n.strip()]
        await self._register_switch(interaction, interaction.user.id, names)

    @switch_group.command(name="out", description="Register switching out (no fronters)")
    async def switch_out_slash(self, interaction: discord.Interaction):
        await self._register_switch(interaction, interaction.user.id, [])

    @switch_group.command(name="delete", description="Delete the latest switch")
    @app_commands.describe(all_switches="Delete all switch history")
    async def switch_delete_slash(self, interaction: discord.Interaction, all_switches: bool = False):
        await self._delete_switch(interaction, interaction.user.id, "all" if all_switches else None)

    @switch_group.command(name="history", description="View switch history")
    async def switch_history_slash(self, interaction: discord.Interaction):
        await self._show_history(interaction, interaction.user.id)

    async def _register_switch(self, ctx, user_id: int, member_names: list[str]):
        try:
            system = await self.get_own_system(user_id)
            member_ids = []
            for name in member_names:
                member = await self.db.find_member(system.id, name)
                if not member:
                    raise member_not_found(name)
                member_ids.append(member.id)

            switch = await self.db.register_switch(system.id, member_ids)

            if not member_ids:
                await self.send_success(ctx, "Switch registered — no one is fronting.")
            else:
                names = []
                for mid in member_ids:
                    m = await self.db.get_member(mid)
                    if m:
                        names.append(f"**{m.name}**")
                await self.send_success(ctx, f"Switch registered! Now fronting: {', '.join(names)}")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _show_current(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            switch = await self.db.get_latest_switch(system.id)
            if not switch or not switch.members:
                await self._respond(ctx, content=f"{NOTE_EMOJI} No fronters registered. Use `pl!switch <member>` to log a switch.")
                return
            names = []
            for mid in switch.members:
                m = await self.db.get_member(mid)
                if m:
                    names.append(f"**{m.name}** (`{m.hid}`)")
            embed = discord.Embed(title="Current Fronters", description="\n".join(names), color=0x7B68EE)
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _delete_switch(self, ctx, user_id: int, scope: str | None):
        try:
            system = await self.get_own_system(user_id)
            if scope and scope.lower() == "all":
                count = await self.db.delete_all_switches(system.id)
                await self.send_success(ctx, f"Deleted {count} switches.")
            else:
                if await self.db.delete_latest_switch(system.id):
                    await self.send_success(ctx, "Latest switch deleted.")
                else:
                    await self._respond(ctx, content=f"{NOTE_EMOJI} No switches to delete.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _show_history(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            history = await self.db.get_switch_history(system.id, 10)
            if not history:
                await self._respond(ctx, content=f"{NOTE_EMOJI} No switch history yet.")
                return
            lines = []
            for sw in history:
                if not sw.members:
                    lines.append(f"**{sw.timestamp}** — *(no fronters)*")
                else:
                    names = []
                    for mid in sw.members:
                        m = await self.db.get_member(mid)
                        if m:
                            names.append(m.name)
                    lines.append(f"**{sw.timestamp}** — {', '.join(names)}")
            embed = discord.Embed(title="Switch History", description="\n".join(lines), color=0x7B68EE)
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(SwitchCog(bot))