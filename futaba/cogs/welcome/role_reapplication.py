#
# cogs/welcome/role_reapplication.py
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
Handling to reapply roles when the member rejoins the guild.
"""

import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import RoleConv, TextChannelConv
from futaba.exceptions import CommandFailed, ManualCheckFailure, SendHelp
from futaba.str_builder import StringBuilder
from futaba.utils import escape_backticks

logger = logging.getLogger(__name__)

__all__ = ["RoleReapplication"]


class RoleReapplication:
    __slots__ = ("bot", "journal")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/roles")

    async def member_update(self, before, after):
        if before.roles == after.roles:
            return

        logger.debug("Member '%s' (%d) roles changed, saving for potential reapplication", after.name, after.id)
        await self.save_roles(after)

    def get_reapply_roles(self, guild):
        logger.debug(
            "Getting possible reapplication roles for guild '%s' (%d)",
            guild.name,
            guild.id,
        )
        can_reapply = []
        special_roles = self.bot.sql.settings.get_special_roles(guild)
        if special_roles.mute_role is not None:
            can_reapply.append(special_roles.mute_role)
        if special_roles.jail_role is not None:
            can_reapply.append(special_roles.jail_role)

        for cog in self.bot.cogs:
            # FIXME better cog detection
            if cog.__name__ == "SelfAssignableRoles":
                can_reapply.extend(cog.get_assignable_roles(guild))
                break

        return can_reapply

    async def reapply_roles(self, member):
        # TODO journal event
        roles = self.bot.sql.roles.get_member_roles(member)
        if not roles:
            logger.debug("No roles to reapply, user is new")
            return

        logger.info(
            "Reapplying roles to member '%s' (%d): [%s]",
            member.name,
            member.id,
            ", ".join(role.name for role in roles),
        )
        await member.add_roles(
            *roles, reason="Automatically reapplying roles", atomic=True
        )

    async def save_roles(self, member):
        # TODO journal event
        logger.info(
            "Member '%s' (%d) updated roles in '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        with self.bot.sql.transaction():
            self.bot.sql.roles.update_member_roles(member)
