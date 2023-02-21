#
# punishment.py
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
Contains commands for handling punishment roles in a modular way.
"""

import logging

logger = logging.getLogger(__name__)

__all__ = ["PunishmentHandler"]


class PunishmentHandler:
    __slots__ = ("bot",)

    def __init__(self, bot):
        self.bot = bot

    def get_role(self, name, guild):
        roles = self.bot.sql.settings.get_special_roles(guild)

        role = getattr(roles, name)
        if role is None:
            logger.warning(
                "No %s role configured for guild '%s' (%d)", name, guild.name, guild.id
            )
            return None

        return role

    async def apply(self, name, guild, member, reason):
        role = self.get_role(name, guild)
        if role is None:
            return

        if member.top_role > guild.me.top_role:
            logger.warning(
                "Lacks permission to %s user '%s' (%d) in guild '%s' (%d)",
                name,
                member.name,
                member.id,
                guild.name,
                guild.id,
            )
            return

        remove_other = self.bot.sql.settings.get_remove_other_roles(guild)
        if remove_other:
            await self.bot.sql.moderation.remove_other_roles(member, role, reason)
        else:
            await member.add_roles(role, reason=reason)

    async def relieve(self, name, guild, member, reason):
        role = self.get_role(name, guild)
        if role is None:
            return

        if member.top_role > guild.me.top_role:
            logger.warning(
                "Lacks permission to %s user '%s' (%d) in guild '%s' (%d)",
                name,
                member.name,
                member.id,
                guild.name,
                guild.id,
            )
            return

        remove_other = self.bot.sql.settings.get_remove_other_roles(guild)
        if remove_other:
            try:
                await self.bot.sql.moderation.restore_other_roles(member, reason)
            except KeyError as error:
                logger.warning(
                    "Received KeyError while restoring other roles: %s", error
                )

        await member.remove_roles(role, reason=reason)

    async def mute(self, guild, member, reason=None):
        logger.info(
            "Muting user '%s' (%d) for reason: %s", member.name, member.id, reason
        )
        await self.apply("mute", guild, member, reason)

    async def jail(self, guild, member, reason=None):
        logger.info(
            "Jailing user '%s' (%d) for reason: %s", member.name, member.id, reason
        )
        await self.apply("jail", guild, member, reason)

    async def focus(self, guild, member, reason=None):
        logger.info(
            "Focusing user '%s' (%d) for reason: %s", member.name, member.id, reason
        )
        await self.apply("focus", guild, member, reason)

    async def unmute(self, guild, member, reason=None):
        logger.info(
            "Unmuting user '%s' (%d) for reason: %s", member.name, member.id, reason
        )
        await self.relieve("mute", guild, member, reason)

    async def unjail(self, guild, member, reason=None):
        logger.info(
            "Unjailing user '%s' (%d) for reason: %s", member.name, member.id, reason
        )
        await self.relieve("jail", guild, member, reason)

    async def unfocus(self, guild, member, reason=None):
        logger.info(
            "Unfocusing user '%s' (%d) for reason: %s", member.name, member.id, reason
        )
        await self.relieve("focus", guild, member, reason)
