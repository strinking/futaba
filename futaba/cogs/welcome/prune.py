#
# cogs/welcome/prune.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Functions to prune a user either manually or automatically
"""

import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from futaba import permissions
from futaba.exceptions import CommandFailed
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Prune"]


def prune_filter(member, prune_date, *, has_roles, lacks_roles):
    """
    Fuction used to filter members by.
    Ensures they have all of the roles in 'has_roles' and doesn't
    have any of the roles in 'lacks_roles'.
    """

    if member.bot:
        return False

    # Ensures that all roles in has_roles exist in member.roles
    for role in has_roles:
        if role not in member.roles:
            return False

    # Ensure that all roles aren't in lacks_roles
    for role in member.roles:
        if role in lacks_roles:
            return False

    return member.joined_at < prune_date


class Prune(AbstractCog):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot
        self.journal = bot.get_broadcaster("/welcome")

    def setup(self):
        pass

    async def prune_member(self, ctx, days):
        """
        Checks if a member has had the guest role for longer than the number of days specified.
        Afterwords, will kick all members that meet that condition.
        """

        # Get guild special roles
        roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        # Get the date that users that join before that have to be pruned
        prune_date = datetime.now() - timedelta(days=days)

        if roles.guest:
            logger.info(
                "Pruning members with role %s (%d) who joined more than %d days ago",
                roles.guest.name,
                roles.guest.id,
                days,
            )

            # Get users to be pruned
            to_be_pruned = filter(
                lambda member: prune_filter(
                    member,
                    prune_date,
                    has_roles={roles.guest},
                    lacks_roles={roles.member, roles.mute, roles.jail, roles.nonpurge},
                ),
                ctx.guild.members,
            )

        elif roles.member is None:
            # If no member role is set the prune command should not do anything
            return None

        else:
            logger.info(
                "Pruning members without role %s (%d) who joined more than %d days ago",
                roles.member.name,
                roles.member.id,
                days,
            )

            # Get users to be pruned
            to_be_pruned = filter(
                lambda member: prune_filter(
                    member,
                    prune_date,
                    has_roles=(),
                    lacks_roles={roles.member, roles.mute, roles.jail, roles.nonpurge},
                ),
                ctx.guild.members,
            )

        count = 0
        for member in to_be_pruned:
            if ctx.me.top_role > member.top_role:
                await ctx.guild.kick(
                    member, reason=f"Pruning guests older than {days} days"
                )
                count += 1
                await asyncio.sleep(0.01)

        return count

    @commands.command(name="prune", aliases=["purge"])
    @commands.guild_only()
    @permissions.check_mod()
    async def prune(self, ctx, days: int = 7):
        """
        Prunes users that have not used the !agree command for at least the given number of days.
        Defaults to seven days.
        """

        pruned_members = await self.prune_member(ctx, days)

        # Check if prune_members is None as if it is there is not member role set
        # If there is no member role set pruning members makes no sense
        if pruned_members is None:
            error_message = (
                "The server has no member role set, so pruning will have no effect"
            )
            embed = discord.Embed(
                description=error_message, colour=discord.Colour.red()
            )
            raise CommandFailed(embed=embed)

        content = f"Pruned {pruned_members} members"
        embed = discord.Embed(description=content, colour=discord.Colour.dark_teal())
        await ctx.send(embed=embed)

        self.journal.send(
            "prune",
            ctx.guild,
            content,
            icon="snip",
            cause=ctx.author,
            members=pruned_members,
        )
