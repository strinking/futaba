#
# cogs/welcome/prune.py
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
Functions to prune a user either manually or automatically
"""

import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from futaba import permissions

logger = logging.getLogger(__name__)

__all__ = ["Prune"]

def prune_filter(member, prune_date, role, has_role=True):
    """
    Fuction used to filter members by.
    If has_role is False it will check if the user dosen't have the role specified
    """
    if has_role:
        if role in member.roles:
            if member.joined_at < prune_date:
                return True
    elif role not in member.roles:
        if member.joined_at < prune_date:
            return True

    return False

class Prune:

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/welcome/prune")

    async def prune_member(self, ctx, days):
        """
        Checks if a member has had the guest role for longer that the days specified.
        Once done will kick all members that meet that condition
        """

        # Get guild special roles
        roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        # Get the date that users that join before that have to be pruned
        prune_date = datetime.now() - timedelta(days=days)

        if roles.guest:
            logger.info("Pruning members with role %s (%d) who joined more than %d days ago", roles.guest.name, roles.guest.id, days)        

            # Get users to be pruned
            to_be_pruned = filter(lambda x: prune_filter(x, prune_date, roles.guest), ctx.guild.members)

        else:
            logger.info("Pruning members without role %s (%d) who joined more than %d days ago", roles.member.name, roles.member.id, days)

            # Get users to be pruned
            to_be_pruned = filter(lambda x: prune_filter(x, prune_date, roles.member, False), ctx.guild.members)

        pruned = []

        for member in to_be_pruned:
            try:
                await ctx.guild.kick(member, reason=f'Pruning guests older than {days} days')
                pruned.append(member)
            except:
                logger.warning("Cannnot prunt member %s (%d)", member.name, member.id)

        return pruned
    
    @commands.command(name="prune", aliases=["purge"])
    @commands.guild_only()
    @permissions.check_admin()
    async def purge(self, ctx, days: int = 7):
        """
        Prunes users that have not used the agree command over the days specified.
        Deafults to seven days
        """

        pruned_members = await self.prune_member(ctx, days)
        

