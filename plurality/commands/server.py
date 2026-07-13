"""Server configuration commands."""

from __future__ import annotations

import json

import discord
from discord import app_commands
from discord.ext import commands

from plurality.commands.base import PluralityCog
from plurality.constants import ERROR_EMOJI, NOTE_EMOJI, SUCCESS_EMOJI
from plurality.utils.discord_utils import check_bot_permissions
from plurality.utils.errors import PluralityError, SyntaxError


class ServerCog(PluralityCog):
    @commands.group(name="blacklist", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def blacklist_prefix(self, ctx: commands.Context):
        await self._show_blacklist(ctx)

    @blacklist_prefix.command(name="add")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_add_prefix(self, ctx: commands.Context, channel: discord.TextChannel):
        await self._blacklist_add(ctx, channel)

    @blacklist_prefix.command(name="remove")
    @commands.has_permissions(manage_guild=True)
    async def blacklist_remove_prefix(self, ctx: commands.Context, channel: discord.TextChannel):
        await self._blacklist_remove(ctx, channel)

    @commands.command(name="permcheck")
    async def permcheck_prefix(self, ctx: commands.Context):
        await self._permcheck(ctx)

    @app_commands.command(name="permcheck", description="Check if Plurality has the required permissions")
    async def permcheck_slash(self, interaction: discord.Interaction):
        await self._permcheck(interaction)

    @app_commands.command(name="setup", description="Interactive setup wizard for new users")
    async def setup_slash(self, interaction: discord.Interaction):
        await self._setup_wizard(interaction)

    async def _show_blacklist(self, ctx):
        if not ctx.guild:
            return
        server = await self.db.get_server(ctx.guild.id)
        blacklist = json.loads(server["blacklist"] if server else "[]")
        if not blacklist:
            await self._respond(ctx, content=f"{NOTE_EMOJI} No channels are blacklisted.")
            return
        channels = [f"<#{c}>" for c in blacklist]
        await self._respond(ctx, content=f"**Blacklisted channels:** {', '.join(channels)}")

    async def _blacklist_add(self, ctx, channel: discord.TextChannel):
        if not ctx.guild:
            return
        server = await self.db.get_server(ctx.guild.id)
        blacklist = json.loads(server["blacklist"] if server else "[]")
        if channel.id not in blacklist:
            blacklist.append(channel.id)
        await self.db.update_server(ctx.guild.id, blacklist=blacklist)
        await self._respond(ctx, content=f"{SUCCESS_EMOJI} {channel.mention} added to proxy blacklist.")

    async def _blacklist_remove(self, ctx, channel: discord.TextChannel):
        if not ctx.guild:
            return
        server = await self.db.get_server(ctx.guild.id)
        blacklist = json.loads(server["blacklist"] if server else "[]")
        blacklist = [c for c in blacklist if c != channel.id]
        await self.db.update_server(ctx.guild.id, blacklist=blacklist)
        await self._respond(ctx, content=f"{SUCCESS_EMOJI} {channel.mention} removed from proxy blacklist.")

    async def _permcheck(self, ctx):
        if not ctx.guild:
            raise SyntaxError("This command must be used in a server.")
        channel = ctx.channel if hasattr(ctx, "channel") else None
        if isinstance(ctx, discord.Interaction):
            channel = ctx.channel
        if not isinstance(channel, discord.TextChannel):
            raise SyntaxError("This command must be used in a text channel.")

        error = check_bot_permissions(channel)
        if error:
            embed = discord.Embed(
                title="Permission Check",
                description=f"{ERROR_EMOJI} {error}",
                color=0xFF4444,
            )
        else:
            embed = discord.Embed(
                title="Permission Check",
                description=f"{SUCCESS_EMOJI} All required permissions are set! Plurality is ready to proxy.",
                color=0x44FF44,
            )
            embed.add_field(
                name="Required Permissions",
                value="• Send Messages\n• Manage Messages\n• Manage Webhooks\n• Read Message History",
                inline=False,
            )
        await self._respond(ctx, embed=embed, ephemeral=True)

    async def _setup_wizard(self, interaction: discord.Interaction):
        system = await self.db.get_system_by_account(interaction.user.id)

        class SetupView(discord.ui.View):
            def __init__(self, cog: ServerCog):
                super().__init__(timeout=300)
                self.cog = cog

            @discord.ui.button(label="Create System", style=discord.ButtonStyle.primary, emoji="✨")
            async def create_system(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if await self.cog.db.get_system_by_account(btn_interaction.user.id):
                    await btn_interaction.response.send_message(
                        f"{NOTE_EMOJI} You already have a system! Use `/system info` to view it.",
                        ephemeral=True,
                    )
                    return
                system = await self.cog.db.create_system(btn_interaction.user.id)
                await btn_interaction.response.send_message(
                    f"{SUCCESS_EMOJI} System `{system.hid}` created! Now add a member.",
                    ephemeral=True,
                )

            @discord.ui.button(label="Add Member", style=discord.ButtonStyle.secondary, emoji="👤")
            async def add_member(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                sys = await self.cog.db.get_system_by_account(btn_interaction.user.id)
                if not sys:
                    await btn_interaction.response.send_message(
                        f"{ERROR_EMOJI} Create a system first!", ephemeral=True
                    )
                    return

                modal = MemberModal(self.cog, sys.id)
                await btn_interaction.response.send_modal(modal)

            @discord.ui.button(label="Enable Autoproxy", style=discord.ButtonStyle.success, emoji="🔄")
            async def enable_autoproxy(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                sys = await self.cog.db.get_system_by_account(btn_interaction.user.id)
                if not sys or not btn_interaction.guild:
                    await btn_interaction.response.send_message(
                        f"{ERROR_EMOJI} Create a system first (in a server)!", ephemeral=True
                    )
                    return
                from plurality.constants import AutoproxyMode
                await self.cog.db.upsert_system_guild(
                    sys.id, btn_interaction.guild.id, autoproxy_mode=AutoproxyMode.FRONT
                )
                await btn_interaction.response.send_message(
                    f"{SUCCESS_EMOJI} Autoproxy enabled in front mode! Log a switch with `/switch register`.",
                    ephemeral=True,
                )

            @discord.ui.button(label="Check Permissions", style=discord.ButtonStyle.secondary, emoji="🔒")
            async def check_perms(self, btn_interaction: discord.Interaction, button: discord.ui.Button):
                if not isinstance(btn_interaction.channel, discord.TextChannel):
                    return
                error = check_bot_permissions(btn_interaction.channel)
                if error:
                    await btn_interaction.response.send_message(f"{ERROR_EMOJI} {error}", ephemeral=True)
                else:
                    await btn_interaction.response.send_message(
                        f"{SUCCESS_EMOJI} All permissions look good!", ephemeral=True
                    )

        class MemberModal(discord.ui.Modal, title="Add a Member"):
            name_input = discord.ui.TextInput(label="Member Name", placeholder="e.g. Luna", max_length=100)
            proxy_input = discord.ui.TextInput(
                label="Proxy Tags (optional)",
                placeholder="e.g. [text] or {text}",
                required=False,
                max_length=50,
            )

            def __init__(self, cog: ServerCog, system_id: int):
                super().__init__()
                self.cog = cog
                self.system_id = system_id

            async def on_submit(self, interaction: discord.Interaction):
                member = await self.cog.db.create_member(self.system_id, self.name_input.value)
                if self.proxy_input.value:
                    from plurality.db.models import ProxyTag
                    val = self.proxy_input.value.strip()
                    tag = None
                    if val.startswith("[") and val.endswith("]"):
                        tag = ProxyTag(prefix="[", suffix="]")
                    elif val.startswith("{") and val.endswith("}"):
                        tag = ProxyTag(prefix="{", suffix="}")
                    if tag:
                        await self.cog.db.update_member(member.id, proxy_tags=[tag])
                await interaction.response.send_message(
                    f"{SUCCESS_EMOJI} Member **{member.name}** created! Try proxying with your tags.",
                    ephemeral=True,
                )

        status = "✅ You have a system!" if system else "❌ No system yet"
        embed = discord.Embed(
            title="Plurality Setup Wizard",
            description=(
                f"Welcome to **Plurality** — the best DID/OSDD proxy bot.\n\n"
                f"**Status:** {status}\n\n"
                "Use the buttons below to get started in seconds. "
                "No complicated commands required!"
            ),
            color=0x7B68EE,
        )
        embed.add_field(
            name="Quick Start",
            value=(
                "1. Create your system\n"
                "2. Add your first member + proxy tags\n"
                "3. Enable autoproxy or use proxy tags\n"
                "4. Check bot permissions"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, view=SetupView(self), ephemeral=True)

    async def _respond(self, ctx, **kwargs):
        if isinstance(ctx, discord.Interaction):
            if ctx.response.is_done():
                await ctx.followup.send(**kwargs)
            else:
                await ctx.response.send_message(**kwargs)
        else:
            await ctx.send(**kwargs)


async def setup(bot: commands.Bot):
    await bot.add_cog(ServerCog(bot))