"""System management commands."""

from __future__ import annotations

from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from plurality.commands.base import PluralityCog
from plurality.constants import NOTE_EMOJI, PrivacyLevel
from plurality.utils.embeds import system_embed
from plurality.utils.errors import PluralityError, SyntaxError
from plurality.utils.privacy import LookupContext


class SystemCog(PluralityCog):
    system_group = app_commands.Group(name="system", description="Manage your system")

    @commands.group(name="system", aliases=["s"], invoke_without_command=True)
    async def system_prefix(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await self._show_system(ctx, ctx.author.id)

    @system_prefix.command(name="new")
    async def system_new_prefix(self, ctx: commands.Context, *, name: str = None):
        await self._create_system(ctx, ctx.author.id, name)

    @system_prefix.command(name="delete")
    async def system_delete_prefix(self, ctx: commands.Context):
        await self._delete_system(ctx, ctx.author.id)

    @system_prefix.command(name="name", aliases=["rename"])
    async def system_name_prefix(self, ctx: commands.Context, *, name: str):
        await self._rename_system(ctx, ctx.author.id, name)

    @system_prefix.command(name="description", aliases=["desc"])
    async def system_desc_prefix(self, ctx: commands.Context, *, description: str = None):
        await self._set_description(ctx, ctx.author.id, description)

    @system_prefix.command(name="tag")
    async def system_tag_prefix(self, ctx: commands.Context, *, tag: str = None):
        await self._set_tag(ctx, ctx.author.id, tag)

    @system_prefix.command(name="proxy")
    async def system_proxy_prefix(self, ctx: commands.Context, state: str = None):
        await self._set_proxy(ctx, ctx.author.id, state)

    @system_prefix.command(name="list")
    async def system_list_prefix(self, ctx: commands.Context):
        await self._list_members(ctx, ctx.author.id)

    @system_prefix.command(name="fronter", aliases=["fronters"])
    async def system_fronter_prefix(self, ctx: commands.Context):
        await self._show_fronters(ctx, ctx.author.id)

    @system_group.command(name="new", description="Create a new system")
    @app_commands.describe(name="Optional name for your system")
    async def system_new_slash(self, interaction: discord.Interaction, name: Optional[str] = None):
        await self._create_system(interaction, interaction.user.id, name)

    @system_group.command(name="info", description="View your system information")
    async def system_info_slash(self, interaction: discord.Interaction):
        await self._show_system(interaction, interaction.user.id)

    @system_group.command(name="delete", description="Delete your system")
    async def system_delete_slash(self, interaction: discord.Interaction):
        await self._delete_system(interaction, interaction.user.id)

    @system_group.command(name="rename", description="Rename your system")
    async def system_rename_slash(self, interaction: discord.Interaction, name: str):
        await self._rename_system(interaction, interaction.user.id, name)

    @system_group.command(name="description", description="Set your system description")
    async def system_desc_slash(self, interaction: discord.Interaction, description: Optional[str] = None):
        await self._set_description(interaction, interaction.user.id, description)

    @system_group.command(name="tag", description="Set your system tag (appended to proxy names)")
    async def system_tag_slash(self, interaction: discord.Interaction, tag: Optional[str] = None):
        await self._set_tag(interaction, interaction.user.id, tag)

    @system_group.command(name="proxy", description="Enable or disable proxying in this server")
    @app_commands.describe(enabled="Whether proxying is enabled")
    async def system_proxy_slash(self, interaction: discord.Interaction, enabled: Optional[bool] = None):
        state = None if enabled is None else ("on" if enabled else "off")
        await self._set_proxy(interaction, interaction.user.id, state)

    @system_group.command(name="members", description="List all members in your system")
    async def system_members_slash(self, interaction: discord.Interaction):
        await self._list_members(interaction, interaction.user.id)

    @system_group.command(name="fronters", description="Show who is currently fronting")
    async def system_fronters_slash(self, interaction: discord.Interaction):
        await self._show_fronters(interaction, interaction.user.id)

    async def _create_system(self, ctx, user_id: int, name: str | None):
        try:
            existing = await self.db.get_system_by_account(user_id)
            if existing:
                raise SyntaxError("You already have a system! Use `pl!system delete` to remove it first.")
            system = await self.db.create_system(user_id, name)
            embed = system_embed(system, LookupContext.OWNER)
            embed.description = (
                f"Welcome to **Plurality**! Your system `{system.hid}` has been created.\n\n"
                "**Next steps:**\n"
                f"• `pl!member new <name>` — add your first member\n"
                f"• `pl!member proxy <name> add [tag]text[/tag]` — set proxy tags\n"
                f"• `pl!autoproxy front` — auto-proxy as your current fronter\n"
                f"• `/setup` — interactive setup wizard"
            )
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _show_system(self, ctx, user_id: int):
        try:
            system = await self.db.get_system_by_account(user_id)
            if not system:
                raise SyntaxError("No system found. Use `pl!system new` to create one!")
            embed = system_embed(system, LookupContext.OWNER)
            members = await self.db.get_members(system.id)
            embed.add_field(name="Members", value=str(len(members)), inline=True)
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _delete_system(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            await self.db.delete_system(system.id)
            await self.send_success(ctx, f"System `{system.hid}` has been deleted.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _rename_system(self, ctx, user_id: int, name: str):
        try:
            system = await self.get_own_system(user_id)
            await self.db.update_system(system.id, name=name)
            await self.send_success(ctx, f"System renamed to **{name}**.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _set_description(self, ctx, user_id: int, description: str | None):
        try:
            system = await self.get_own_system(user_id)
            await self.db.update_system(system.id, description=description)
            if description:
                await self.send_success(ctx, "System description updated.")
            else:
                await self._respond(ctx, content=f"{NOTE_EMOJI} System description cleared.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _set_tag(self, ctx, user_id: int, tag: str | None):
        try:
            system = await self.get_own_system(user_id)
            await self.db.update_system(system.id, tag=tag)
            if tag:
                await self.send_success(ctx, f"System tag set to `{tag}`.")
            else:
                await self._respond(ctx, content=f"{NOTE_EMOJI} System tag cleared.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _set_proxy(self, ctx, user_id: int, state: str | None):
        try:
            system = await self.get_own_system(user_id)
            guild = self._get_guild(ctx)
            if not guild:
                raise SyntaxError("This command must be used in a server.")

            if state is None:
                sg = await self.db._fetchone(
                    "SELECT proxy_enabled FROM system_guild WHERE system = ? AND guild = ?",
                    (system.id, guild.id),
                )
                enabled = sg["proxy_enabled"] if sg else True
                await self._respond(
                    ctx,
                    content=f"{NOTE_EMOJI} Proxying is **{'enabled' if enabled else 'disabled'}** in this server.",
                )
                return

            enabled = state.lower() in ("on", "enable", "yes", "true", "1")
            await self.db.upsert_system_guild(system.id, guild.id, proxy_enabled=enabled)
            await self.send_success(
                ctx, f"Proxying **{'enabled' if enabled else 'disabled'}** in this server."
            )
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _list_members(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            guild = self._get_guild(ctx)
            members = await self.db.get_members(system.id, guild.id if guild else None)
            if not members:
                await self._respond(ctx, content=f"{NOTE_EMOJI} No members yet. Use `pl!member new <name>` to add one!")
                return
            lines = [f"**{m.display_name or m.name}** (`{m.hid}`)" for m in members[:50]]
            if len(members) > 50:
                lines.append(f"...and {len(members) - 50} more")
            embed = discord.Embed(
                title=f"Members of {system.name or system.hid}",
                description="\n".join(lines),
                color=0x7B68EE,
            )
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _show_fronters(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            switch = await self.db.get_latest_switch(system.id)
            if not switch or not switch.members:
                await self._respond(ctx, content=f"{NOTE_EMOJI} No one is currently registered as fronting.")
                return
            names = []
            for mid in switch.members:
                m = await self.db.get_member(mid)
                if m:
                    names.append(f"**{m.display_name or m.name}** (`{m.hid}`)")
            embed = discord.Embed(
                title="Current Fronters",
                description="\n".join(names),
                color=0x7B68EE,
            )
            if switch.timestamp:
                embed.set_footer(text=f"Since {switch.timestamp}")
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    def _get_guild(self, ctx) -> discord.Guild | None:
        if isinstance(ctx, discord.Interaction):
            return ctx.guild
        return ctx.guild

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(SystemCog(bot))