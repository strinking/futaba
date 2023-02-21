#
# cogs/roles/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License.  You are free to redistribute and/or modify it under those
# terms.  It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY.  See the LICENSE file for more details.
#
"""
Cog for maintaining a guild's list of self-assignable roles, roles which
do not provide any special permissions, but are markers that members can
add to themselves if they wish.
"""

import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import RoleConv, TextChannelConv
from futaba.exceptions import CommandFailed, ManualCheckFailure, SendHelp
from futaba.str_builder import StringBuilder
from futaba.utils import escape_backticks, user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)


class SelfAssignableRoles(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/roles")

        # Load self-assignable roles from database
        for guild in bot.guilds:
            bot.sql.roles.get_assignable_roles(guild)
            bot.sql.roles.get_role_command_channels(guild)

    def setup(self):
        pass

    async def check_channel(self, ctx):
        ok_channels = self.bot.sql.roles.get_role_command_channels(ctx.guild)

        # Any channel is allowed
        if not ok_channels:
            return

        # This channel is allowed
        if ctx.channel in ok_channels:
            return

        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name="Cannot use role commands there!")
        embed.description = (
            f"You attempted to use the command `{escape_backticks(ctx.message.content)}` "
            f"in {ctx.channel.mention}. The moderators have set it so that role assignment "
            "commands can only be used in the following channels:\n"
            f"{', '.join(channel.mention for channel in ok_channels)}\n"
        )

        try:
            await ctx.author.send(embed=embed)
        except discord.Forbidden:
            await ctx.send(content="Please enable direct messages.")
        raise CommandFailed()

    @commands.group(name="role", aliases=["sar"])
    @commands.guild_only()
    async def role(self, ctx):
        """Manages self-assignable roles for this guild."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @role.command(name="show", aliases=["display", "list", "lsar", "ls"])
    @commands.guild_only()
    async def role_show(self, ctx):
        """Shows all self-assignable roles."""

        await self.check_channel(ctx)

        assignable_roles = sorted(
            self.bot.sql.roles.get_assignable_roles(ctx.guild), key=lambda r: r.name
        )
        if not assignable_roles:
            prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No self-assignable roles")
            embed.description = (
                f"Moderators can use the `{prefix}role joinable/unjoinable` "
                "commands to change this list!"
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Self-assignable roles")

        descr = StringBuilder(sep=", ")
        for role in assignable_roles:
            descr.write(role.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)

    @role.command(name="pshow", aliases=["pdisplay", "plist", "plsar", "pls"])
    @commands.guild_only()
    async def pingable_show(self, ctx):
        """Shows all channels where a role is pingable."""
        logger.info(
            "Displaying pingable channels and roles in guild '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        # r[0] == current channel.
        channel_role = sorted(
            self.bot.sql.roles.get_pingable_role_channels(ctx.guild),
            key=lambda r: r[0].name,
        )

        if not channel_role:
            prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No pingable roles in this guild")
            embed.description = (
                f"Moderators can use the `{prefix}role pingable/unpingable` "
                "commands to change this list!"
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Pingable roles (channel, role)")

        descr = StringBuilder(sep="\n")
        for channel, role in channel_role:
            descr.write(f"{channel.mention}: {role.mention}")
        embed.description = str(descr)
        await ctx.send(embed=embed)

    def check_roles(self, ctx, roles):
        if not roles:
            raise CommandFailed()

        assignable_roles = self.bot.sql.roles.get_assignable_roles(ctx.guild)
        for role in roles:
            if role not in assignable_roles:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name="Role not assignable")
                embed.description = f"The role {role.mention} cannot be self-assigned"
                raise CommandFailed(embed=embed)

            if role >= ctx.me.top_role:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name="Error assigning roles")
                embed.description = (
                    f"Cannot assign {role.mention}, which is above me in the hierarchy"
                )
                raise ManualCheckFailure(embed=embed)

    @staticmethod
    def str_roles(roles):
        return " ".join(f"`{role.name}`" for role in roles)

    @role.command(name="add", aliases=["join", "give", "set", "update"])
    @commands.guild_only()
    async def role_add(self, ctx, *roles: RoleConv):
        """Joins the given self-assignable roles."""

        if not roles:
            return

        await self.check_channel(ctx)
        self.check_roles(ctx, roles)
        await ctx.author.add_roles(
            *roles, reason="Adding self-assignable roles", atomic=True
        )

        content = f"{user_discrim(ctx.author)} added self-assignable roles: {self.str_roles(roles)}"
        self.journal.send("self/add", ctx.guild, content, icon="role")

    @role.command(
        name="remove", aliases=["rm", "delete", "del", "leave", "take", "unset"]
    )
    @commands.guild_only()
    async def role_remove(self, ctx, *roles: RoleConv):
        """Leaves the given self-assignable roles."""

        if not roles:
            return

        await self.check_channel(ctx)
        self.check_roles(ctx, roles)
        await ctx.author.remove_roles(
            *roles, reason="Removing self-assignable roles", atomic=True
        )

        content = f"{user_discrim(ctx.author)} removed self-assignable roles: {self.str_roles(roles)}"
        self.journal.send("self/remove", ctx.guild, content, icon="role")

    @staticmethod
    def str_channels(channels):
        return " ".join(f"`{channel.name}`" for channel in channels)

    @role.command(name="createhelperrole", aliases=["chr"])
    @commands.guild_only()
    @permissions.check_mod()
    async def helper_role_add(self, ctx, role: RoleConv, *channels: TextChannelConv):
        logger.info(
            "Adding automatically managed helper role (base '%s') for guild '%s' (%d) in channels [%s]",
            role.name,
            ctx.guild.name,
            ctx.guild.id,
            self.str_channels(channels),
        )

        helper_role = self.bot.sql.roles.get_pingable_role_from_original(
            ctx.guild, role
        )
        unadded_channels = frozenset(channels) - frozenset(
            self.bot.sql.roles.get_channels_from_role(ctx.guild, helper_role)
        )
        if not unadded_channels:
            raise CommandFailed("No channels were affected")
        if not helper_role:
            helper_role = await ctx.guild.create_role(
                name=f"{role.name} (helper)", colour=role.colour
            )
        await self.role_joinable(ctx, helper_role)
        await self.role_pingable(ctx, helper_role, *unadded_channels, original=role)

    @role.command(name="removehelperrole", aliases=["deletehelperrole", "rmhr", "dhr"])
    @commands.guild_only()
    @permissions.check_mod()
    async def helper_role_remove(self, ctx, role: RoleConv, *args):
        logger.info(
            "Removing automatically managed helper role '%s' for guild '%s' (%d)",
            role.name,
            ctx.guild.name,
            ctx.guild.id,
        )

        if len(args) == 1:
            if args[0] == "-h":
                helper_role = self.bot.sql.roles.get_pingable_role_from_original(
                    ctx.guild, role
                )
                if not helper_role:
                    role = None
                else:
                    role = discord.utils.get(ctx.guild.roles, id=helper_role.id)
            else:
                raise CommandFailed("Unknown argument")
        channels = self.bot.sql.roles.get_channels_from_role(ctx.guild, role)
        if not channels or not role:
            raise CommandFailed("Role was not pingable or did not exist to begin with")
        await self.role_unpingable(ctx, role, *channels)
        await self.role_unjoinable(ctx, role)
        await role.delete()

    @role.command(name="joinable", aliases=["assignable", "canjoin"])
    @commands.guild_only()
    @permissions.check_mod()
    async def role_joinable(self, ctx, *roles: RoleConv):
        """Allows a moderator to add roles to the self-assignable group."""

        logger.info(
            "Adding joinable roles for guild '%s' (%d): [%s]",
            ctx.guild.name,
            ctx.guild.id,
            ", ".join(role.name for role in roles),
        )

        if not roles:
            raise CommandFailed()

        # Get special roles
        special_roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        # Ensure none of the roles grant any permissions
        for role in roles:
            embed = permissions.elevated_role_embed(ctx.guild, role, "error")
            if embed is not None:
                raise ManualCheckFailure(embed=embed)

            for attr in ("member", "guest", "mute", "jail"):
                if role == getattr(special_roles, attr):
                    embed = discord.Embed(colour=discord.Colour.red())
                    embed.set_author(name="Cannot add role as assignable")
                    embed.description = (
                        f"{role.mention} cannot be self-assignable, "
                        f"it is already used as the **{attr}** role!"
                    )
                    raise ManualCheckFailure(embed=embed)

        # Get roles that are already assignable
        assignable_roles = self.bot.sql.roles.get_assignable_roles(ctx.guild)

        # Add roles to database
        with self.bot.sql.transaction():
            for role in roles:
                if role not in assignable_roles:
                    self.bot.sql.roles.add_assignable_role(ctx.guild, role)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Made roles joinable")
        descr = StringBuilder(sep=", ")
        for role in roles:
            descr.write(role.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)

        # Send journal event
        content = f"Roles were set as joinable: {self.str_roles(roles)}"
        self.journal.send("joinable/add", ctx.guild, content, icon="role", roles=roles)

    @role.command(
        name="unjoinable", aliases=["unassignable", "cantjoin", "cannotjoin", "nojoin"]
    )
    @commands.guild_only()
    @permissions.check_mod()
    async def role_unjoinable(self, ctx, *roles: RoleConv):
        """Allows a moderator to remove roles from the self-assignable group."""

        logger.info(
            "Removing joinable roles for guild '%s' (%d): [%s]",
            ctx.guild.name,
            ctx.guild.id,
            ", ".join(role.name for role in roles),
        )

        if not roles:
            raise CommandFailed()

        # Remove roles from database
        with self.bot.sql.transaction():
            for role in roles:
                self.bot.sql.roles.remove_assignable_role(ctx.guild, role)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Made roles not joinable")
        descr = StringBuilder(sep=", ")
        for role in roles:
            descr.write(role.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)

        # Send journal event
        content = f"Roles were set as not joinable: {self.str_roles(roles)}"
        self.journal.send(
            "joinable/remove", ctx.guild, content, icon="role", roles=roles
        )

    @role.command(name="pingable")
    @commands.guild_only()
    @permissions.check_mod()
    async def role_pingable(
        self, ctx, role: RoleConv, *channels: TextChannelConv, original=None
    ):
        logger.info(
            "Making role '%s' pingable in guild '%s' (%d), channel(s) [%s]",
            role.name,
            ctx.guild.name,
            ctx.guild.id,
            self.str_channels(channels),
        )

        if not channels:
            raise CommandFailed()

        # self.bot.sql.roles.get_pingable_role_channels(ctx.guild) gets a set
        # of tuples (channel, role).
        # Zip converts it into a set of channels and a set of roles.
        channel_role = zip(*self.bot.sql.roles.get_pingable_role_channels(ctx.guild))
        # this makes a list of all channels and rows, currently it's a channel and row pair.
        # next gets the next item from the zip iterator which is the set of channels.
        # if the iterator is exhausted i.e there's no pingable channels, the default value set() will be used.
        pingable_channels = next(channel_role, set())

        # channels that were already in the database will not be added, user
        # will be informed.
        exempt_channels = []

        with self.bot.sql.transaction():
            for channel in channels:
                if channel not in pingable_channels:
                    self.bot.sql.roles.add_pingable_role_channel(
                        ctx.guild, channel, role, original
                    )
                else:
                    exempt_channels.append(channel)

        if exempt_channels:
            embed = discord.Embed(colour=discord.Colour.dark_grey())
            embed.set_author(name="Failed to make role pingable in channels: ")
            descr = StringBuilder(sep=", ")
            for channel in exempt_channels:
                descr.write(channel.mention)
            embed.description = str(descr)
            await ctx.send(embed=embed)
            # Did not put the embed in CommandFailed.  All channels must fail
            # to be added for the entire command to 'fail', imo.
            if set(exempt_channels) == set(channels):
                raise CommandFailed()

        # Send journal event
        content = f"Role was set as pingable in channels: {self.str_channels(channels)}, except {self.str_channels(exempt_channels)}"
        self.journal.send(
            "pingable/add",
            ctx.guild,
            content,
            icon="role",
            role=role,
            channels=channels,
        )

    @role.command(name="unpingable")
    @commands.guild_only()
    @permissions.check_mod()
    async def role_unpingable(self, ctx, role: RoleConv, *channels: TextChannelConv):
        logger.info(
            "Making role '%s' not pingable in guild '%s' (%d), channel(s) [%s]",
            role.name,
            ctx.guild.name,
            ctx.guild.id,
            self.str_channels(channels),
        )

        if not channels:
            raise CommandFailed()

        # See role_pingable for an explanation
        channel_role = zip(*self.bot.sql.roles.get_pingable_role_channels(ctx.guild))
        pingable_channels = next(channel_role, set())

        exempt_channels = []

        with self.bot.sql.transaction():
            for channel in channels:
                if channel in pingable_channels:
                    self.bot.sql.roles.remove_pingable_role_channel(
                        ctx.guild, channel, role
                    )
                else:
                    exempt_channels.append(channel)

        if exempt_channels:
            embed = discord.Embed(colour=discord.Colour.dark_grey())
            embed.set_author(name="Failed to make role unpingable in channels: ")
            descr = StringBuilder(sep=", ")
            for channel in exempt_channels:
                descr.write(channel.mention)
            embed.description = str(descr)
            await ctx.send(embed=embed)
            if set(exempt_channels) == set(channels):
                raise CommandFailed()

        # Send journal event
        content = f"Role was set as not pingable in channels: {self.str_channels(channels)}, except {self.str_channels(exempt_channels)}"
        self.journal.send(
            "pingable/remove",
            ctx.guild,
            content,
            icon="role",
            role=role,
            channels=channels,
        )

    def channel_journal(self, guild):
        all_channels = self.bot.sql.roles.get_role_command_channels(guild)
        str_channels = " ".join(chan.mention for chan in all_channels)
        content = f"Allowed channels for bot commands set: {str_channels or '(any)'}"
        self.journal.send(
            "channel/set", guild, content, icon="channel", channels=list(all_channels)
        )

    @role.command(name="addchan", aliases=["addchans", "addchannel", "addchannels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_add(self, ctx, *channels: TextChannelConv):
        """Adds the channel(s) to the restricted role channel list."""

        logger.info(
            "Allowing channels to be used for role commands in guild '%s' (%d): [%s]",
            ctx.guild.name,
            ctx.guild.id,
            ", ".join(channel.name for channel in channels),
        )

        if not channels:
            raise CommandFailed()

        # Add channels to database
        with self.bot.sql.transaction():
            for channel in channels:
                self.bot.sql.roles.add_role_command_channel(ctx.guild, channel)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Allowed channels to be used for adding roles")
        descr = StringBuilder(sep=", ")
        all_channels = self.bot.sql.roles.get_role_command_channels(ctx.guild)
        for channel in all_channels:
            descr.write(channel.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)

        # Send journal event
        self.channel_journal(ctx.guild)

    @role.command(name="setchan", aliases=["setchans", "setchannel", "setchannels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_set(self, ctx, *channels: TextChannelConv):
        """Overwrites the channel(s) in the restricted role channel list to exactly this."""

        logger.info(
            "Setting channels to be used for role commands in guild '%s' (%d): [%s]",
            ctx.guild.name,
            ctx.guild.id,
            ", ".join(channel.name for channel in channels),
        )

        if not channels:
            raise CommandFailed()

        # Write new channel list to database
        with self.bot.sql.transaction():
            self.bot.sql.roles.remove_all_role_command_channels(ctx.guild)
            for channel in channels:
                self.bot.sql.roles.add_role_command_channel(ctx.guild, channel)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Set channels to be used for adding roles")
        descr = StringBuilder(sep=", ")
        for channel in channels:
            descr.write(channel.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)

        # Send journal event
        self.channel_journal(ctx.guild)

    @role.command(
        name="delchan",
        aliases=[
            "delchans",
            "delchannel",
            "delchannels",
            "deletechannel",
            "deletechannels",
        ],
    )
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_delete(self, ctx, *channels: TextChannelConv):
        """Removes the channel(s) from the restricted role channel list."""

        logger.info(
            "Removing channels to be used for role commands in guild '%s' (%d): [%s]",
            ctx.guild.name,
            ctx.guild.id,
            ", ".join(channel.mention for channel in channels),
        )

        if not channels:
            raise CommandFailed()

        # Remove channels from database
        with self.bot.sql.transaction():
            for channel in channels:
                self.bot.sql.roles.remove_role_command_channel(ctx.guild, channel)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Removed channels to be used for adding roles")

        all_channels = self.bot.sql.roles.get_role_command_channels(ctx.guild)
        descr = StringBuilder(sep=", ")
        for channel in channels:
            descr.write(channel.mention)
        embed.add_field(name="Removed", value=str(descr))

        descr.clear()
        for channel in all_channels:
            descr.write(channel.mention)
        embed.add_field(name="Remaining", value=str(descr) or "(none)")
        await ctx.send(embed=embed)

        # Send journal event
        self.channel_journal(ctx.guild)

    @role.command(name="anychan", aliases=["anychans", "anychannel", "anychannels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_any(self, ctx):
        """
        Allows the use of any channel for role commands.
        This has the effect of clearing the list.
        """

        logger.info(
            "Removing all channels used for role commands in guild '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        # Remove channels from database
        with self.bot.sql.transaction():
            self.bot.sql.roles.remove_all_role_command_channels(ctx.guild)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Allowed any channel to be used for role commands")
        embed.description = "Removed all channels in the restricted list."
        await ctx.send(embed=embed)

        # Send journal event
        self.channel_journal(ctx.guild)

    @role.command(name="chan", aliases=["chans", "channel", "channels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_show(self, ctx):
        """Lists all channels that are allowed to be used for role commands."""

        all_channels = self.bot.sql.roles.get_role_command_channels(ctx.guild)
        prefix = self.bot.prefix(ctx.guild)
        if all_channels:
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.set_author(name="Permitted channels")
            descr = StringBuilder(sep=", ")
            for channel in all_channels:
                descr.write(channel.mention)
            embed.description = str(descr)
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="All channels are permitted")
            embed.description = (
                f"There are no restricted role channels set, so `{prefix}role add/remove` commands "
                "can be used anywhere."
            )

        await ctx.send(embed=embed)
