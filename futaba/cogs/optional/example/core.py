#
# cogs/optional/example/core.py
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
Example optional cog.
"""

# REMOVE THIS IN REGULAR COGS:
# pylint: disable=unused-import

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

        # Get previous number, if any
        #
        # This is a JSON blob stored persistently.
        # It can take whatever form or schema is most appropriate for the cog.
        settings = self.bot.sql.settings.get_optional_cog_settings(ctx.guild, "example")
        previous = settings.get("example-command-previous", 0.0)

        # Build response
        embed = discord.Embed(colour=discord.Colour.teal())
        embed.set_author(name=f"Input: {number}, Previous: {previous}")
        embed.description = (
            f"Square root: `{math.sqrt(abs(number + previous))}`\n"
            f"Natural logarithm: `{math.log(abs(number + previous))}`\n"
            f"Sine / cosine: `{math.sin(number + previous)}` / `{math.cos(number + previous)}`"
        )
        await ctx.send(embed=embed)

        # Save previous number
        #
        # You need to save the entire settings blob, not just the fields you updated.
        settings["example-command-previous"] = number
        self.bot.sql.settings.set_optional_cog_settings(ctx.guild, "example", settings)

        # Send journal event
        content = f"Test command, inputted number: {number}, previous: {previous}"
        self.journal.send(
            "command", ctx.guild, content, icon="ok", number=number, previous=previous
        )
