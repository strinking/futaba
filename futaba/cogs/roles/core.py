#
# cogs/roles/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
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
from futaba.utils import escape_backticks

logger = logging.getLogger(__package__)


class SelfAssignableRoles:
    __slots__ = ("bot", "journal")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/roles")

        # Load self-assignable roles from database
        for guild in bot.guilds:
            bot.sql.roles.get_assignable_roles(guild)

    @staticmethod
    async def author_send(ctx, **kwargs):
        try:
            await ctx.author.send(**kwargs)
        except discord.Forbidden:
            await ctx.send(content="Please enable direct messages.")

    async def check_channel(self, ctx):
        ok_channels = self.bot.sql.get_role_command_channels(ctx.guild)

        # Any channel is allowed
        if not ok_channels:
            return

        # This channel is allowed
        if ctx.channel in ok_channels:
            return

        embed = discord.Embed(colour=discord.Colour.red())
        embed.set_author(name="Cannot use role commands there!")
        embed.description = (
            f"You attempted to use the command `{escape_backticks(ctx.content)}` in "
            "{ctx.channel.mention}. The moderators have set it so that role assignment "
            "commands can only be used in the following channels:\n"
            f"{', '.join(channel.name for channel in ok_channels)}\n"
        )

        await self.author_send(ctx, embed=embed)
        raise CommandFailed()

    @commands.group(name="role", aliases=["sar"])
    @commands.guild_only()
    async def role(self, ctx):
        """ Manages self-assignable roles for this guild. """

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @role.command(name="show", aliases=["display", "list", "lsar", "ls"])
    @commands.guild_only()
    async def role_show(self, ctx):
        """ Shows all self-assignable roles. """

        assignable_roles = sorted(
            self.bot.sql.roles.get_assignable_roles(ctx.guild), key=lambda r: r.name
        )
        if not assignable_roles:
            prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No self-assignable roles")
            embed.description = f"Moderators can use the `{prefix}role joinable/unjoinable` commands to change this list!"
            await self.author_send(ctx, embed=embed)
            return

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Self-assignable roles")

        descr = StringBuilder(sep=", ")
        for role in assignable_roles:
            descr.write(role.mention)
        embed.description = str(descr)

        await self.author_send(ctx, embed=embed)

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
            elif role >= ctx.me.top_role:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name="Error assigning roles")
                embed.description = (
                    f"Cannot assign {role.mention}, which is above me in the hierarchy"
                )
                raise ManualCheckFailure(embed=embed)

    @role.command(name="add", aliases=["join", "give", "set", "update"])
    @commands.guild_only()
    async def role_add(self, ctx, *roles: RoleConv):
        """ Joins the given self-assignable roles. """

        self.check_roles(ctx, roles)
        await ctx.author.add_roles(
            *roles, reason="Adding self-assignable roles", atomic=True
        )

    @role.command(
        name="remove", aliases=["rm", "delete", "del", "leave", "take", "unset"]
    )
    @commands.guild_only()
    async def role_remove(self, ctx, *roles: RoleConv):
        """ Leaves the given self-assignable roles. """

        self.check_roles(ctx, roles)
        await ctx.author.remove_roles(
            *roles, reason="Removing self-assignable roles", atomic=True
        )

    @role.command(name="joinable", aliases=["assignable", "canjoin"])
    @commands.guild_only()
    @permissions.check_mod()
    async def role_joinable(self, ctx, *roles: RoleConv):
        """ Allows a moderator to add roles to the self-assignable group. """

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

    @role.command(
        name="unjoinable", aliases=["unassignable", "cantjoin", "cannotjoin", "nojoin"]
    )
    @commands.guild_only()
    @permissions.check_mod()
    async def role_unjoinable(self, ctx, *roles: RoleConv):
        """ Allows a moderator to remove roles from the self-assignable group. """

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

    @role.command(name="addchan", aliases=["addchans", "addchannel", "addchannels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_add(self, ctx, *channels: TextChannelConv):
        """ Adds the channel(s) to the restricted role channel list. """

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

    @role.command(name="setchan", aliases=["setchans", "setchannel", "setchannels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_set(self, ctx, *channels: TextChannelConv):
        """ Overwrites the channel(s) in the restricted role channel list to exactly this. """

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
        """ Removes the channel(s) from the restricted role channel list. """

        logger.info(
            "Removing channels to be used for role commands in guild '%s' (%d): [%s]",
            ctx.guild.name,
            ctx.guild.id,
            ", ".join(channel for channel in channels),
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

    @role.command(name="chan", aliases=["chans", "channel", "channels"])
    @commands.guild_only()
    @permissions.check_mod()
    async def channel_show(self, ctx):
        """ Lists all channels that are allowed to be used for role commands. """

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

        await self.author_send(ctx, embed=embed)
