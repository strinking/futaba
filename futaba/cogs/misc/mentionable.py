#
# cogs/misc/mentionable.py
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
Cog for automatically checking and enforcing un-mentionable names.
"""

import logging
import random
import string

import discord
from discord.ext import commands

from futaba.utils import plural, user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Mentionable"]

MAX_NAME_LENGTH = 32
PREFIX_CHARACTERS = f"{string.ascii_letters}{string.digits}"
TYPEABLE_CHARACTERS = f"{PREFIX_CHARACTERS}!\"'$%&()*+,-./:;<=>?[\\]^_`{{|}}~"


class Mentionable(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/mentionable")

    def setup(self):
        pass

    @staticmethod
    def invalid_name(prefix, name):
        head = name[:prefix]
        for ch in head:
            if ch not in TYPEABLE_CHARACTERS:
                return True
        return False

    @staticmethod
    def random_prefix(length):
        return "".join(random.choice(PREFIX_CHARACTERS) for _ in range(length))

    @staticmethod
    async def notify_user(member, length):
        try:
            prefix = member.nick[:length]
            await member.send(
                content=(
                    f"Your name in __{member.guild.name}__ is not easily mentionable due to special "
                    f"characters.\nModerators there have required that **at least {length} "
                    f"character{plural(length)} at the beginning of your name are easily typeable**\n"
                    f"This message to inform you that you have been given the random prefix `{prefix}` "
                    "to make you mentionable in chat."
                )
            )
        except discord.Forbidden:
            logger.debug("Cannot PM user '%s' (%d) about unmentionable name")

    async def enforce_mentionable_name(self, member):
        # Check member permissions
        myself = member.guild.me
        if member.top_role >= myself.top_role:
            return

        prefix = self.bot.sql.settings.get_mentionable_name_prefix(member.guild)
        renick = None

        # Check username and nickname
        if member.nick is not None:
            if self.invalid_name(prefix, member.nick):
                renick = f"{self.random_prefix(prefix)}{member.nick}"

        if renick is None:
            if self.invalid_name(prefix, member.name):
                renick = f"{self.random_prefix(prefix)}{member.name}"

        # Apply nickname change
        if renick is not None:
            renick = renick[:MAX_NAME_LENGTH]

            await member.edit(
                nick=renick,
                reason=f"Unmentionable username, applying random prefix of {prefix}",
            )
            await self.notify_user(member, prefix)

            content = f"{user_discrim(member)} given mentionable nickname: {renick}"
            self.journal.send("renick", member.guild, content, icon="reference")

    async def member_join(self, member):
        await self.enforce_mentionable_name(member)

    async def member_update(self, before, after):
        await self.enforce_mentionable_name(after)
