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
from collections import namedtuple

import discord
from discord.ext import commands

from futaba.converters import UserConv
from futaba.str_builder import StringBuilder
from futaba.utils import user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)
FakeMember = namedtuple("FakeMember", ("name", "id", "guild"))

__all__ = ["RoleReapplication"]


class RoleReapplication(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/roles")

    def setup(self):
        with self.bot.sql.transaction():
            for member in self.bot.get_all_members():
                self.bot.sql.roles.update_saved_roles(member)

    async def member_update(self, before, after):
        if before.roles == after.roles:
            return

        special_roles = self.bot.sql.settings.get_special_roles(after.guild)
        if special_roles.guest_role in after.roles:
            return

        logger.debug(
            "Member '%s' (%d) roles changed, saving for potential reapplication",
            after.name,
            after.id,
        )
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
        """ Returns all roles that would be reapplied when a given user rejoins. """

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

        content = f"Reapplied roles to {member.mention}: {', '.join(role.mention for role in roles)}"
        self.journal.send(
            "reapply", member.guild, content, member=member, roles=roles, icon="role"
        )

    async def save_roles(self, member):
        logger.info(
            "Member '%s' (%d) updated roles in '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        with self.bot.sql.transaction():
            self.bot.sql.roles.update_saved_roles(member)

        content = f"Saved updated roles for {user_discrim(member)}"
        self.journal.send("save", member.guild, content, member=member, icon="save")
