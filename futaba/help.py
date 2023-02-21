#
# help.py
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
Implements modifications to the discord.py help provider class.
"""

import logging

import discord
from discord.ext import commands

from .utils import user_discrim
from .enums import Reactions

logger = logging.getLogger(__name__)


class HelpCommand(commands.DefaultHelpCommand):
    def __init__(self):
        super().__init__(width=90, sort_commands=True, dm_help=True, indent=4)

    async def on_help_command_error(self, ctx, error):
        async with ctx.bot.message_lock(ctx.message):
            try:
                await self.handle_error(ctx, error)
            except discord.NotFound:
                pass

    async def handle_error(self, ctx, error):
        reported = False
        await Reactions.DENY.add(ctx.message)

        if isinstance(error, commands.errors.CommandInvokeError):
            error = error.__cause__

            if isinstance(error, discord.Forbidden):
                logger.debug(
                    "Lacks permissions to send help to %s (%d)",
                    user_discrim(ctx.author),
                    ctx.author.id,
                )

                embed = discord.Embed(colour=discord.Colour.red())
                embed.title = "Cannot send help command"
                embed.description = (
                    "You do not allow DMs from this server. "
                    "Please enable them so help information can be sent."
                )

                reported = True
                await ctx.send(embed=embed)

        # Default error handling
        if not reported:
            logger.error("Unexpected error raised during help command", exc_info=error)
            await ctx.bot.report_other_exception(
                ctx, error, "Unexpected error occurred during help command!"
            )
