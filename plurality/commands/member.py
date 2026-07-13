"""Member management commands."""

from __future__ import annotations

import re
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from plurality.commands.base import PluralityCog
from plurality.constants import NOTE_EMOJI
from plurality.db.models import ProxyTag
from plurality.utils.embeds import member_embed
from plurality.utils.errors import PluralityError, SyntaxError, member_not_found
from plurality.utils.privacy import LookupContext


PROXY_TAG_PATTERN = re.compile(r"^(.+?)\{(.+?)\}(.*)$|^\[(.+?)\](.*)$|^(.+?)\|(.*)$")


class MemberCog(PluralityCog):
    member_group = app_commands.Group(name="member", description="Manage system members")

    @commands.group(name="member", aliases=["m"], invoke_without_command=True)
    async def member_prefix(self, ctx: commands.Context, *, name: str = None):
        if ctx.invoked_subcommand is None and name:
            await self._show_member(ctx, ctx.author.id, name)

    @member_prefix.command(name="new")
    async def member_new_prefix(self, ctx: commands.Context, *, name: str):
        await self._create_member(ctx, ctx.author.id, name)

    @member_prefix.command(name="delete")
    async def member_delete_prefix(self, ctx: commands.Context, *, name: str):
        await self._delete_member(ctx, ctx.author.id, name)

    @member_prefix.command(name="rename")
    async def member_rename_prefix(self, ctx: commands.Context, member: str, *, new_name: str):
        await self._rename_member(ctx, ctx.author.id, member, new_name)

    @member_prefix.command(name="proxy")
    async def member_proxy_prefix(self, ctx: commands.Context, member: str, action: str = None, *, tags: str = None):
        await self._manage_proxy(ctx, ctx.author.id, member, action, tags)

    @member_prefix.command(name="description", aliases=["desc"])
    async def member_desc_prefix(self, ctx: commands.Context, member: str, *, description: str = None):
        await self._set_description(ctx, ctx.author.id, member, description)

    @member_prefix.command(name="pronouns")
    async def member_pronouns_prefix(self, ctx: commands.Context, member: str, *, pronouns: str = None):
        await self._set_pronouns(ctx, ctx.author.id, member, pronouns)

    @member_prefix.command(name="displayname")
    async def member_display_prefix(self, ctx: commands.Context, member: str, *, display_name: str = None):
        await self._set_display_name(ctx, ctx.author.id, member, display_name)

    @member_group.command(name="new", description="Create a new member")
    @app_commands.describe(name="The member's name")
    async def member_new_slash(self, interaction: discord.Interaction, name: str):
        await self._create_member(interaction, interaction.user.id, name)

    @member_group.command(name="info", description="View member information")
    @app_commands.autocomplete(name=PluralityCog.member_autocomplete)
    async def member_info_slash(self, interaction: discord.Interaction, name: str):
        await self._show_member(interaction, interaction.user.id, name)

    @member_group.command(name="delete", description="Delete a member")
    @app_commands.autocomplete(name=PluralityCog.member_autocomplete)
    async def member_delete_slash(self, interaction: discord.Interaction, name: str):
        await self._delete_member(interaction, interaction.user.id, name)

    @member_group.command(name="rename", description="Rename a member")
    @app_commands.autocomplete(member=PluralityCog.member_autocomplete)
    async def member_rename_slash(self, interaction: discord.Interaction, member: str, new_name: str):
        await self._rename_member(interaction, interaction.user.id, member, new_name)

    @member_group.command(name="proxy", description="Add or remove proxy tags")
    @app_commands.describe(
        member="Member name",
        action="add, remove, or clear",
        tags="Proxy tags like [text] or prefix|suffix",
    )
    @app_commands.autocomplete(member=PluralityCog.member_autocomplete)
    async def member_proxy_slash(
        self, interaction: discord.Interaction, member: str, action: str, tags: Optional[str] = None
    ):
        await self._manage_proxy(interaction, interaction.user.id, member, action, tags)

    @member_group.command(name="description", description="Set member description")
    @app_commands.autocomplete(member=PluralityCog.member_autocomplete)
    async def member_desc_slash(
        self, interaction: discord.Interaction, member: str, description: Optional[str] = None
    ):
        await self._set_description(interaction, interaction.user.id, member, description)

    @member_group.command(name="pronouns", description="Set member pronouns")
    @app_commands.autocomplete(member=PluralityCog.member_autocomplete)
    async def member_pronouns_slash(
        self, interaction: discord.Interaction, member: str, pronouns: Optional[str] = None
    ):
        await self._set_pronouns(interaction, interaction.user.id, member, pronouns)

    async def _resolve_member(self, user_id: int, name: str, guild_id: int | None = None):
        system = await self.get_own_system(user_id)
        member = await self.db.find_member(system.id, name, guild_id)
        if not member:
            raise member_not_found(name)
        return system, member

    async def _create_member(self, ctx, user_id: int, name: str):
        try:
            system = await self.get_own_system(user_id)
            member = await self.db.create_member(system.id, name)
            embed = member_embed(member, LookupContext.OWNER)
            embed.description = (
                f"Member **{member.name}** created!\n\n"
                f"Set proxy tags: `pl!member proxy {member.name} add [text]`\n"
                f"Or use `/member proxy` for an easier experience."
            )
            await self._respond(ctx, embed=embed)
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _show_member(self, ctx, user_id: int, name: str):
        try:
            guild = ctx.guild if hasattr(ctx, "guild") else None
            guild_id = guild.id if guild else None
            _, member = await self._resolve_member(user_id, name, guild_id)
            await self._respond(ctx, embed=member_embed(member, LookupContext.OWNER))
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _delete_member(self, ctx, user_id: int, name: str):
        try:
            _, member = await self._resolve_member(user_id, name)
            await self.db.delete_member(member.id)
            await self.send_success(ctx, f"Member **{member.name}** deleted.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _rename_member(self, ctx, user_id: int, member_name: str, new_name: str):
        try:
            _, member = await self._resolve_member(user_id, member_name)
            await self.db.update_member(member.id, name=new_name)
            await self.send_success(ctx, f"Member renamed to **{new_name}**.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _set_description(self, ctx, user_id: int, member_name: str, description: str | None):
        try:
            _, member = await self._resolve_member(user_id, member_name)
            await self.db.update_member(member.id, description=description)
            await self.send_success(ctx, "Member description updated.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _set_pronouns(self, ctx, user_id: int, member_name: str, pronouns: str | None):
        try:
            _, member = await self._resolve_member(user_id, member_name)
            await self.db.update_member(member.id, pronouns=pronouns)
            await self.send_success(ctx, "Member pronouns updated.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _set_display_name(self, ctx, user_id: int, member_name: str, display_name: str | None):
        try:
            _, member = await self._resolve_member(user_id, member_name)
            await self.db.update_member(member.id, display_name=display_name)
            await self.send_success(ctx, "Member display name updated.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    async def _manage_proxy(self, ctx, user_id: int, member_name: str, action: str | None, tags: str | None):
        try:
            _, member = await self._resolve_member(user_id, member_name)

            if action is None:
                if not member.proxy_tags:
                    await self._respond(ctx, content=f"{NOTE_EMOJI} **{member.name}** has no proxy tags.")
                else:
                    tag_list = ", ".join(f"`{t.prefix}text{t.suffix}`" for t in member.proxy_tags)
                    await self._respond(ctx, content=f"Proxy tags for **{member.name}**: {tag_list}")
                return

            action = action.lower()
            if action == "clear":
                await self.db.update_member(member.id, proxy_tags=[])
                await self.send_success(ctx, f"All proxy tags cleared for **{member.name}**.")
                return

            if action == "remove":
                if not tags:
                    raise SyntaxError("Specify which tags to remove.")
                parsed = self._parse_proxy_tag(tags)
                new_tags = [
                    t for t in member.proxy_tags
                    if not (t.prefix == parsed.prefix and t.suffix == parsed.suffix)
                ]
                await self.db.update_member(member.id, proxy_tags=new_tags)
                await self.send_success(ctx, f"Proxy tag removed from **{member.name}**.")
                return

            if action in ("add", "set"):
                if not tags:
                    raise SyntaxError(
                        "Specify proxy tags. Examples: `[text]`, `{text}`, `V|text|V`, or `:: text ::`"
                    )
                parsed = self._parse_proxy_tag(tags)
                new_tags = list(member.proxy_tags) + [parsed] if action == "add" else [parsed]
                await self.db.update_member(member.id, proxy_tags=new_tags)
                await self.send_success(
                    ctx,
                    f"Proxy tag `{parsed.prefix}text{parsed.suffix}` set for **{member.name}**.",
                )
                return

            raise SyntaxError(f"Unknown action `{action}`. Use add, remove, or clear.")
        except PluralityError as e:
            await self.send_error(ctx, e)

    def _parse_proxy_tag(self, text: str) -> ProxyTag:
        text = text.strip()
        if text.startswith("[") and text.endswith("]"):
            return ProxyTag(prefix="[", suffix="]")
        if text.startswith("{") and text.endswith("}"):
            return ProxyTag(prefix="{", suffix="}")
        if "|" in text:
            parts = text.split("|", 1)
            if len(parts) == 2:
                return ProxyTag(prefix=parts[0], suffix=parts[1] if parts[1] else "")
        if text.startswith("::") and text.endswith("::"):
            return ProxyTag(prefix=":: ", suffix=" ::")
        if len(text) >= 2:
            return ProxyTag(prefix=text[0], suffix=text[-1])
        raise SyntaxError(
            "Couldn't parse proxy tags. Try `[text]`, `{text}`, `prefix|suffix`, or `:: text ::`"
        )

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(MemberCog(bot))