#
# cogs/misc/debug.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

""" Cog for miscellaneous owner-only debugging commands. """

import asyncio
import logging
import sys

import aiohttp
import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions
from futaba.utils import plural
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Debugging"]


class Debugging(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/debug")

    def setup(self):
        pass

    @commands.command(name="queuesize", aliases=["qsize"], hidden=True)
    @permissions.check_admin()
    async def queue_size(self, ctx):
        """Displays how many journal events are in the delayed queue."""

        qsize = len(self.bot.queue)
        embed = discord.Embed(colour=discord.Colour.teal())
        embed.description = (
            f"There are currently `{qsize}` item{plural(qsize)} in the delayed queue.\n"
            f"Every `{self.bot.config.delay_chunk_size}` entries the loop will sleep for "
            f"`{self.bot.config.delay_sleep:.3f}` seconds."
        )
        await ctx.send(embed=embed)

    @commands.command(name="testlong", aliases=["testwait"], hidden=True)
    @permissions.check_owner()
    async def test_long_command(self, ctx, delay: float = 4.0):
        """A command that is always successful, but takes a long time to finish."""

        await asyncio.sleep(abs(delay))

    @commands.command(name="testerror", hidden=True)
    @permissions.check_owner()
    async def test_error(self, ctx):
        """Deliberately raises an exception to test the bot's error handling."""

        self.journal.send(
            "error/runtime", ctx.guild, "Raising runtime error", icon="error"
        )
        raise RuntimeError("Intentionally raised exception")

    @commands.command(name="testnetworkerror", aliases=["testneterror"], hidden=True)
    @permissions.check_owner()
    async def test_network_error(self, ctx):
        """
        Deliberately raises a network error to test the bot's spurious network failure handling.
        """

        self.journal.send(
            "error/network", ctx.guild, "Raising aiohttp network error", icon="error"
        )
        raise aiohttp.ClientError()

    @commands.command(name="shutdown", aliases=["halt"], hidden=True)
    @permissions.check_owner()
    async def shutdown(self, ctx):
        """Shuts down the bot. Can only able be run by an owner."""

        self.journal.send(
            "admin/shutdown", ctx.guild, "Shutting down bot", icon="shutdown"
        )
        await Reactions.SUCCESS.add(ctx.message)
        sys.exit()
