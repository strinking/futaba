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

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import RoleConv
from futaba.exceptions import CommandFailed, ManualCheckFailure, SendHelp
from futaba.str_builder import StringBuilder

logger = logging.getLogger(__package__)


class SelfAssignableRoles:
    __slots__ = ("bot", "journal")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/roles")

    @commands.group(name="role", aliases=["roles", "sar"])
    @commands.guild_only()
    async def role(self, ctx):
        """ Manages self-assignable roles for this guild. """

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @role.command(name="show", aliases=["display", "list", "lsar", "ls"])
    @commands.guild_only()
    async def role_show(self, ctx):
        """ Shows all self-assignable roles. """

        ...

    @role.command(name="add", aliases=["join", "give", "set", "update"])
    @commands.guild_only()
    async def role_add(self, ctx, *roles: RoleConv):
        """ Joins the given self-assignable roles. """

        if not roles:
            raise CommandFailed()

        ...

    @role.command(
        name="remove", aliases=["rm", "delete", "del", "leave", "take", "unset"]
    )
    @commands.guild_only()
    async def role_remove(self, ctx, *roles: RoleConv):
        """ Leaves the given self-assignable roles. """

        if not roles:
            raise CommandFailed()

        ...

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

        # Ensure none of the roles grant any permissions
        for role in roles:
            embed = permissions.elevated_role_embed(ctx.guild, role, "error")
            if embed is not None:
                raise ManualCheckFailure(embed=embed)

        # Add roles to database
        with self.bot.sql.transaction():
            for role in roles:
                self.bot.sql.roles.add_assignable_role(ctx.guild, role)

    @role.command(name="unjoinable", aliases=["unassignable", "cannotjoin", "nojoin"])
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

        # Make a copy of joinable roles before the delete
        assignable_roles = frozenset(self.bot.sql.roles.get_assignable_roles(ctx.guild))

        # Remove roles from database
        with self.bot.sql.transaction():
            for role in roles:
                self.bot.sql.roles.remove_assignable_role(ctx.guild, role)

        # Send response if not all roles were removed
        not_removed = frozenset(roles) - assignable_roles
        if not_removed:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="Not all roles removed")
            descr = StringBuilder()
            descr.writeln("The following roles were not assignable to begin with:")
            for role in not_removed:
                descr.writeln(f"- {role.mention}")
            embed.description = str(descr)
            await ctx.send(embed=embed)
