#
# cogs/misc/mentionable.py
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
Cog for automatically checking and enforcing un-mentionable names.
"""

import asyncio
import logging
import random
import string

import discord
from discord.ext import commands

from futaba import permissions
from futaba.utils import plural, user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Mentionable"]

MAX_NAME_LENGTH = 32
PREFIX_CHARACTERS = f"{string.ascii_letters}{string.digits}"
TYPEABLE_CHARACTERS = f"{PREFIX_CHARACTERS}!\"'$%&()*+,-./:;<=>?[\\]^_`{{|}}~ "


class Mentionable(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/mentionable")

    def setup(self):
        pass

    @staticmethod
    def invalid_name(prefix, name):
        # Ignore if no nickname is set
        if name is None:
            return False

        head = name[:prefix]
        for ch in head:
            if ch not in TYPEABLE_CHARACTERS:
                return True
        return False

    @staticmethod
    def random_prefix(length):
        return "".join(random.choice(PREFIX_CHARACTERS) for _ in range(length))

    async def notify_user(self, member, prefix):
        try:
            length = self.bot.sql.settings.get_mentionable_name_prefix(member.guild)

            await member.send(
                content=(
                    f"Your name in __{member.guild.name}__ is not easily mentionable due to special "
                    f"characters.\nModerators there have required that **at least {length} "
                    f"character{plural(length)} at the beginning of your name are easily typeable**.\n"
                    f"You that you have been given the random prefix `{prefix}` to make you "
                    "mentionable in chat."
                )
            )
        except discord.Forbidden:
            logger.info("Cannot PM user '%s' (%d) about unmentionable name")

    def check_mentionable_name(self, member):
        # Check member permissions
        myself = member.guild.me
        if member.top_role >= myself.top_role:
            return False

        if member.bot:
            return False

        prefix = self.bot.sql.settings.get_mentionable_name_prefix(member.guild)
        bad_name = self.invalid_name(prefix, member.name)
        bad_nick = self.invalid_name(prefix, member.nick)
        return bad_name and bad_nick

    async def enforce_mentionable_name(self, member):
        if not self.check_mentionable_name(member):
            return False

        length = self.bot.sql.settings.get_mentionable_name_prefix(member.guild)
        prefix = self.random_prefix(length)
        nick = f"{prefix}{member.display_name}"
        nick = nick[:MAX_NAME_LENGTH]

        await member.edit(
            nick=nick,
            reason=f"Unmentionable username, applying random prefix of {prefix}",
        )
        await self.notify_user(member, prefix)

        content = f"{user_discrim(member)} given mentionable nickname: {nick}"
        self.journal.send(
            "enforce",
            member.guild,
            content,
            icon="reference",
            member=member,
            prefix=prefix,
            nick=nick,
        )
        return True

    async def member_join(self, member):
        await self.enforce_mentionable_name(member)

    async def member_update(self, before, after):
        await self.enforce_mentionable_name(after)

    @commands.command(name="ensurementionable", aliases=["ensuremention", "fmention"])
    @commands.guild_only()
    @permissions.check_mod()
    async def ensure_members_mentionable(self, ctx, enforce: bool = False):
        """
        Processes all members and checks if they are mentionable by guild policy or not.
        Requires a true argument to run in enforce mode.
        """

        if enforce:
            count = 0
            for member in ctx.guild.members:
                did_enforce = await self.enforce_mentionable_name(member)
                count += int(did_enforce)
                await asyncio.sleep(0.01)
        else:
            count = sum(
                1 for member in ctx.guild.members if self.check_mentionable_name(member)
            )

        embed = discord.Embed()
        embed.colour = discord.Colour.dark_teal()
        embed.set_author(
            name=f"Mentionable members {'enforcement' if enforce else 'report'}"
        )
        verb = "were" if enforce else "would be"
        embed.description = f"`{count}` members {verb} given mentionable nicknames"
        await ctx.send(embed=embed)
