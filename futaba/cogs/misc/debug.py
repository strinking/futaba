#
# cogs/misc/debug.py
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
Cog for miscellaneous owner-only debugging commands.
"""

import logging

import aiohttp
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__name__)

__all__ = ["Debugging"]


class Debugging:
    __slots__ = ("bot", "journal")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/debug")

    @commands.command(name="testerror", hidden=True)
    @permissions.check_owner()
    async def test_error(self, ctx):
        """ Deliberately raises an exception to test the bot's error handling. """

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
        """ Shuts down the bot. Can only able be run by an owner. """

        self.journal.send(
            "admin/shutdown", ctx.guild, "Shutting down bot", icon="shutdown"
        )
        await Reactions.SUCCESS.add(ctx.message)
        exit()
