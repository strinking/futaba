#
# punishment.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Contains commands for handling punishment roles in a modular way.
"""

import asyncio
import logging

import discord

logger = logging.getLogger(__name__)

class PunishmentHandler:
    __slots__ = (
        "bot",
    )

    def __init__(self, bot):
        self.bot = bot

    def check_other_roles(self, member):
        has_other, punish_role, _ = self.bot.sql.moderation.get_other_roles(member)
        if has_other:
            embed = discord.Embed(colour=discord.Colour.red())
            role_descr = (
                ""
                if punish_role is None
                else f"because they already have {punish_role.mention}"
            )
            embed.description = (
                f"Cannot add a new overriding role to {member.mention} {role_descr}"
            )
            raise CommandFailed(embed=embed)

    def get_role(self, name):
        roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        role = getattr(roles, name)
        if role is None:
            logger.error("No %s role configured for guild '%s' (%d)", name, guild.name, guild.id)

        return role

    async def apply(self, action, guild, member, reason):
        role = self.get_role(action)
        if role is None:
            return

        if member.top_role > guild.me.top_role:
            logger.error("Lacks permission to %s user '%s' (%d) in guild '%s' (%d)", action, member.name, member.id, guild.name, guild.id)
            return

        remove_other = self.bot.sql.settings.get_remove_other_roles(guild)
        if remove_other:
            self.check_other_roles(member)
            await self.bot.sql.moderation.remove_other_roles(member, role, reason)
        else:
            await member.add_roles(role, reason=reason)

    async def mute(self, guild, member, reason = None):
        logger.info("Muting user '%s' (%d) for reason: %s", member.name, member.id, reason)
        await self.apply('mute', guild, member, reason)

    async def jail(self, guild, member, reason = None):
        logger.info("Jailing user '%s' (%d) for reason: %s", member.name, member.id, reason)
        await self.apply('jail')

    async def relieve(self, action, guild, member, reason):
        ...

    async def unmute(self, guild, member, reason = None):
        logger.info("Unmuting user '%s' (%d)", member.name, member.id)

        role = self.get_role('mute')
        if role is None:
            return

        if member.top_role > guild.me.top_role:
            logger.error("Lacks permission to unmute user '%s' (%d) in guild '%s' (%d)", member.name, member.id, guild.name, guild.id)
            return

        remove_other = self.bot.sql.settings.get_remove_other_roles(guild)
        # TODO finish

