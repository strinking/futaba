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

        # Load self-assignable roles from database
        for guild in bot.guilds:
            bot.sql.roles.get_assignable_roles(guild)

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

        assignable_roles = sorted(self.bot.sql.roles.get_assignable_roles(ctx.guild), key=lambda r: r.name)
        if not assignable_roles:
            prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name='No self-assignable roles')
            embed.description = f'Use the `{prefix}role joinable/unjoinable` commands to change this list!'
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name='Self-assignable roles')

        descr = StringBuilder(sep=', ')
        for role in assignable_roles:
            descr.write(role.mention)
        embed.description = str(descr)

        await ctx.send(embed=embed)

    def check_roles(self, ctx, roles):
        if not roles:
            raise CommandFailed()

        assignable_roles = self.bot.sql.roles.get_assignable_roles(ctx.guild)
        for role in roles:
            if role not in assignable_roles:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name='Role not assignable')
                embed.description = f'The role {role.mention} cannot be self-assigned'
                raise CommandFailed(embed=embed)
            elif role >= ctx.me.top_role:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name='Error assigning roles')
                embed.description = f'Cannot assign {role.mention}, which is above me in the hierarchy'
                raise ManualCheckFailure(embed=embed)

    @role.command(name="add", aliases=["join", "give", "set", "update"])
    @commands.guild_only()
    async def role_add(self, ctx, *roles: RoleConv):
        """ Joins the given self-assignable roles. """

        self.check_roles(ctx, roles)
        await ctx.author.add_roles(roles, reason='Adding self-assignable roles', atomic=True)

    @role.command(
        name="remove", aliases=["rm", "delete", "del", "leave", "take", "unset"]
    )
    @commands.guild_only()
    async def role_remove(self, ctx, *roles: RoleConv):
        """ Leaves the given self-assignable roles. """

        self.check_roles(ctx, roles)
        await ctx.author.remove_roles(roles, reason='Removing self-assignable roles', atomic=True)

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

        # Get roles that are already assignable
        assignable_roles = self.bot.sql.roles.get_assignable_roles(ctx.guild)

        # Add roles to database
        with self.bot.sql.transaction():
            for role in roles:
                if role not in assignable_roles:
                    self.bot.sql.roles.add_assignable_role(ctx.guild, role)

        # Send response
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name='Made roles joinable')
        descr = StringBuilder(sep=', ')
        for role in roles:
            descr.write(role.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)

    @role.command(name="unjoinable", aliases=["unassignable", "cantjoin", "cannotjoin", "nojoin"])
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
        embed.set_author(name='Made roles not joinable')
        descr = StringBuilder(sep=', ')
        for role in roles:
            descr.write(role.mention)
        embed.description = str(descr)
        await ctx.send(embed=embed)
