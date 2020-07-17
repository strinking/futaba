#
# cogs/optional/statbot/core.py
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
Cog for querying a local statbot database.
"""

import logging
from urllib.parse import urlencode
from typing import Union

import discord
from discord.ext import commands

from futaba import permissions
from futaba.cogs.abc import AbstractCog
from futaba.converters import TextChannelConv, UserConv
from futaba.str_builder import StringBuilder
from futaba.utils import fancy_timedelta, plural
from .sql import StatbotSqlHandler
from .utils import int_hash

logger = logging.getLogger(__name__)


class Statbot(AbstractCog):
    __slots__ = ("journal", "sql")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/statbot")
        self.sql = StatbotSqlHandler(bot.config.optional_cogs["statbot"]["url"])

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

        params = {}
        for item in items:
            if isinstance(item, discord.TextChannel):
                params["channel_id"] = item.id
            elif isinstance(item, discord.abc.User):
                params["int_user_id"] = int_hash(item.id)

        await ctx.send(
            content=f"https://ddd.raylu.net/guild/{ctx.guild.id}/{'?' if params else ''}{urlencode(params)}"
        )

    @commands.command(
        name="msgcount", aliases=["messagecount", "msgstat", "messagestat"]
    )
    @commands.guild_only()
    @permissions.check_mod()
    async def message_count(self, ctx, user: UserConv, *exclude: TextChannelConv):
        """
        Gets the total number of messages this user has sent in the guild.
        Text channels to exclude from the search can be added as optional arguments.
        """

        message_count, edited_count, deleted_count = self.sql.message_count(
            ctx.guild, user, exclude
        )

        descr = StringBuilder()
        descr.writeln(
            f"Found `{message_count}` message{plural(message_count)} from {user.mention}."
        )

        if message_count:
            descr.writeln(
                f"Of those, `{edited_count}` (or `{edited_count / message_count * 100:.2f}%`) are edited,\n"
                f"and `{deleted_count}` (or `{deleted_count / message_count * 100:.2f}%`) are deleted."
            )

        if hasattr(user, "joined_at"):
            descr.writeln()
            descr.writeln(
                f"They have been a member for {fancy_timedelta(user.joined_at)}."
            )

        embed = discord.Embed(colour=discord.Colour.teal())
        embed.description = str(descr)

        await ctx.send(embed=embed)
