#
# cogs/optional/example/core.py
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
Example optional cog.
"""

import asyncio
import logging
import math

import discord
from discord.ext import commands

from futaba import permissions
from futaba.cogs.abc import AbstractCog
from futaba.exceptions import CommandFailed

logger = logging.getLogger(__name__)


class ExampleCog(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/example")

    def setup(self):
        # Fetching information from the database for this cog
        pass

    @commands.command(name="examplecommand")
    @commands.guild_only()
    async def command(self, ctx, number: float = 0):
        """
        Example command for optional cogs.
        """

        embed = discord.Embed(colour=discord.Colour.teal())
        embed.set_author(name="Input: {number}")
        embed.description = (
            f"Square root: {math.sqrt(number)}\n"
            f"Natural logarithm: {math.log(number)}\n"
            f"Sine / cosine: {math.sin(number)} / {math.cos(number)}"
        )
        await ctx.send(embed=embed)

        self.journal.send(
            "command", ctx, f"Test command, inputted number: {number}", icon="ok"
        )
