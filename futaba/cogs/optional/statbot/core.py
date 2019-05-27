#
# cogs/optional/statbot/core.py
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
Cog for querying a local statbot database.
"""

import asyncio
import hashlib
import logging
import struct
from urllib.parse import urlencode
from typing import Union

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import TextChannelConv, UserConv
from futaba.cogs.abc import AbstractCog
from futaba.exceptions import CommandFailed

logger = logging.getLogger(__name__)


def int_hash(num):
    """
    The integer hashing algorithm used by Statbot to transform real user IDs.
    """

    data = struct.pack(">q", num)
    hashed = hashlib.sha512(data).digest()
    (result,) = struct.unpack(">q", hashed[24:32])
    return result


class StatbotCog(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/statbot")

    def setup(self):
        # Fetching information from the database for this cog
        pass

    @commands.command(name="ddd", aliases=["dddlink", "dddurl"])
    @commands.guild_only()
    @permissions.check_mod()
    async def ddd(self, ctx, *items: Union[TextChannelConv, UserConv]):
        """
        Gets the ddd (Discord Data Delver, by raylu) link for the item specified.
        """

        logger.info(
            "Producing ddd link for guild '%s' (%d) [%d arguments]",
            ctx.guild.name,
            ctx.guild.id,
            len(items),
        )

        base_link = f"https://ddd.raylu.net/guild/{ctx.guild.id}/"
        params = {}

        for item in items:
            if isinstance(item, discord.TextChannel):
                params["channel_id"] = item.id
            elif isinstance(item, discord.abc.User):
                params["int_user_id"] = int_hash(item.id)

        await ctx.send(content=f"{base_link}{'?' if params else ''}{urlencode(params)}")
