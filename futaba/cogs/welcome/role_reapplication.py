#
# cogs/welcome/role_reapplication.py
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
Handling to reapply roles when the member rejoins the guild.
"""

import asyncio
import logging
from collections import deque, namedtuple

import discord
from discord.ext import commands

from futaba.converters import UserConv
from futaba.utils import user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)
FakeMember = namedtuple("FakeMember", ("name", "id", "guild"))

__all__ = ["RoleReapplication"]


class RoleReapplication(AbstractCog):
    __slots__ = ("journal", "lock", "recent_updates")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/roles")
        self.lock = asyncio.Lock()
        self.recent_updates = deque(maxlen=20)

    async def bg_setup(self):
        """
        Update all of the member's saved roles.

        Since this task can be very slow with several thousand members,
        the task is run in the background delays itself to avoid clogging
        the bot. However, this will degrade reapply-role performance until
        it's finished.
        """

        async with self.lock:
            with self.bot.sql.transaction():
                for i, member in enumerate(self.bot.get_all_members()):
                    self.bot.sql.roles.update_saved_roles(member)

                    if i % 20 == 0:
                        await asyncio.sleep(0.2)

    def setup(self):
        logger.info("Running member role update in background")
        self.bot.loop.create_task(self.bg_setup())

    async def member_update(self, before, after):
        if before.roles == after.roles:
            return

        entry = (before, after)
        if entry in self.recent_updates:
            return
        else:
            self.recent_updates.append(entry)

        special_roles = self.bot.sql.settings.get_special_roles(after.guild)
        if special_roles.guest_role in after.roles:
            return

        await self.save_roles(after)

    def get_reapply_roles(self, guild):
        logger.debug(
            "Getting possible reapplication roles for guild '%s' (%d)",
            guild.name,
            guild.id,
        )

        reapply_roles = self.bot.sql.settings.get_reapply_roles(guild)
        can_reapply = list(reapply_roles)

        special_roles = self.bot.sql.settings.get_special_roles(guild)
        if special_roles.mute_role is not None:
            can_reapply.append(special_roles.mute_role)
        if special_roles.jail_role is not None:
            can_reapply.append(special_roles.jail_role)

        if "SelfAssignableRoles" in self.bot.cogs:
            can_reapply.extend(self.bot.sql.roles.get_assignable_roles(guild))

        return can_reapply

    def get_roles_to_reapply(self, member):
        roles = self.bot.sql.roles.get_saved_roles(member)
        if not roles:
            logger.debug("No roles to reapply, user is new")
            return None

        can_reapply = self.get_reapply_roles(member.guild)
        return list(filter(lambda r: r in can_reapply, roles))

    @commands.guild_only()
    @commands.command(name="savedroles", aliases=["saveroles", "userroles", "uroles"])
    async def saved_roles(self, ctx, user: UserConv = None):
        """Returns all roles that would be reapplied when a given user rejoins."""

        if user is None:
            member = ctx.author
            mention = ctx.author.mention
        else:
            member = FakeMember(id=user.id, name=user.name, guild=ctx.guild)
            mention = user.mention

        roles = self.get_roles_to_reapply(member)
        if roles:
            roles.sort(key=lambda r: r.position, reverse=True)
            role_list = " ".join(role.mention for role in roles)
            sep = "\n\n" if len(roles) > 3 else " "

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.title = "\N{MILITARY MEDAL} Roles which would be applied on join"
            embed.description = f"{mention}:{sep}{role_list}"
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = f"No roles are saved for {mention}."
        await ctx.send(embed=embed)

    async def reapply_roles(self, member):
        roles = self.get_roles_to_reapply(member)
        if roles is None:
            return None

        logger.info(
            "Reapplying roles to member '%s' (%d): [%s]",
            member.name,
            member.id,
            ", ".join(role.name for role in roles),
        )
        await member.add_roles(
            *roles, reason="Automatically reapplying roles", atomic=True
        )

        content = (
            f"Reapplied roles to {member.mention}: {', '.join(f'`{role.name}`' for role in roles)}"
            if roles
            else f"Reapplied no roles to {member.mention}"
        )
        self.journal.send(
            "reapply", member.guild, content, member=member, roles=roles, icon="role"
        )
        return roles

    async def save_roles(self, member):
        logger.info(
            "Member '%s' (%d) updated roles in '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        async with self.lock:
            with self.bot.sql.transaction():
                self.bot.sql.roles.update_saved_roles(member)

        content = f"Saved updated roles for {user_discrim(member)}"
        self.journal.send("save", member.guild, content, member=member, icon="save")
