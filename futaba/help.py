#
# help.py
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
Implements modifications to the discord.py help provider class.
"""

import asyncio
import logging

import discord
from discord.ext import commands

from .utils import user_discrim
from .enums import Reactions

logger = logging.getLogger(__name__)


class HelpCommand(commands.DefaultHelpCommand):
    def __init__(self, client):
        super().__init__(
            width=90, sort_commands=True, dm_help=True, indent=4,
        )

        self.client = client

    async def on_help_command_error(self, ctx, error):
        async with self.client.message_lock(ctx.message):
            try:
                await self.handle_error(ctx, error)
            except discord.NotFound:
                pass

    async def handle_error(self, ctx, error):
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

            await asyncio.gather(
                ctx.send(embed=embed), Reactions.DENY.add(ctx.message),
            )

        else:
            logger.error("Unknown discord command error raised", exc_info=error)
            await self.client.report_other_exception(
                ctx, error, "Unwrapped exception was raised from command!",
            )
