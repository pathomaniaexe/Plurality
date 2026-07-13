"""Group management commands."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from plurality.commands.base import PluralityCog
from plurality.constants import NOTE_EMOJI
from plurality.utils.errors import PluralityError, SyntaxError, member_not_found


class GroupCog(PluralityCog):
    group_group = app_commands.Group(name="group", description="Manage member groups")

    @commands.group(name="group", aliases=["g"], invoke_without_command=True)
    async def group_prefix(self, ctx: commands.Context, *, name: str = None):
        if ctx.invoked_subcommand is None:
            if name:
                await self._show_group(ctx, ctx.author.id, name)
            else:
                await self._list_groups(ctx, ctx.author.id)

    @group_prefix.command(name="new")
    async def group_new_prefix(self, ctx: commands.Context, *, name: str):
        await self._create_group(ctx, ctx.author.id, name)

    @group_prefix.command(name="add")
    async def group_add_prefix(self, ctx: commands.Context, group: str, *members: str):
        await self._add_members(ctx, ctx.author.id, group, list(members))

    @group_prefix.command(name="remove")
    async def group_remove_prefix(self, ctx: commands.Context, group: str, *members: str):
        await self._remove_members(ctx, ctx.author.id, group, list(members))

    @group_group.command(name="new", description="Create a new group")
    async def group_new_slash(self, interaction: discord.Interaction, name: str):
        await self._create_group(interaction, interaction.user.id, name)

    @group_group.command(name="list", description="List all groups")
    async def group_list_slash(self, interaction: discord.Interaction):
        await self._list_groups(interaction, interaction.user.id)

    @group_group.command(name="add", description="Add members to a group")
    async def group_add_slash(self, interaction: discord.Interaction, group: str, members: str):
        names = [n.strip() for n in members.split(",")]
        await self._add_members(interaction, interaction.user.id, group, names)

    async def _create_group(self, ctx, user_id: int, name: str):
        try:
            system = await self.get_own_system(user_id)
            group = await self.db.create_group(system.id, name)
            await self.send_success(ctx, f"Group **{group.name}** created (`{group.hid}`).")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _list_groups(self, ctx, user_id: int):
        try:
            system = await self.get_own_system(user_id)
            groups = await self.db.get_groups(system.id)
            if not groups:
                await self._respond(ctx, content=f"{NOTE_EMOJI} No groups yet. Use `pl!group new <name>` to create one.")
                return
            lines = [f"**{g.display_name or g.name}** (`{g.hid}`)" for g in groups]
            embed = discord.Embed(title="Groups", description="\n".join(lines), color=0x7B68EE)
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _show_group(self, ctx, user_id: int, name: str):
        try:
            system = await self.get_own_system(user_id)
            group = await self.db.find_group(system.id, name)
            if not group:
                raise SyntaxError(f"Couldn't find group `{name}`.")
            members = await self.db.get_group_members(group.id)
            embed = discord.Embed(
                title=group.display_name or group.name,
                description=group.description,
                color=0x7B68EE,
            )
            if members:
                embed.add_field(
                    name="Members",
                    value=", ".join(m.name for m in members),
                    inline=False,
                )
            embed.set_footer(text=f"ID: {group.hid}")
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _add_members(self, ctx, user_id: int, group_name: str, member_names: list[str]):
        try:
            system = await self.get_own_system(user_id)
            group = await self.db.find_group(system.id, group_name)
            if not group:
                raise SyntaxError(f"Couldn't find group `{group_name}`.")
            added = []
            for name in member_names:
                member = await self.db.find_member(system.id, name)
                if not member:
                    raise member_not_found(name)
                await self.db.add_group_member(group.id, member.id)
                added.append(member.name)
            await self.send_success(ctx, f"Added {', '.join(added)} to **{group.name}**.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _remove_members(self, ctx, user_id: int, group_name: str, member_names: list[str]):
        try:
            system = await self.get_own_system(user_id)
            group = await self.db.find_group(system.id, group_name)
            if not group:
                raise SyntaxError(f"Couldn't find group `{group_name}`.")
            for name in member_names:
                member = await self.db.find_member(system.id, name)
                if member:
                    await self.db.remove_group_member(group.id, member.id)
            await self.send_success(ctx, f"Members removed from **{group.name}**.")
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
    await bot.add_cog(GroupCog(bot))