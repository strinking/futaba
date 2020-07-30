#
# cogs/optional/simplewriter/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5, Joshua 'joshuas3' Stockin
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
A thing that only lets you write stuff in a certain word box, but only if it's made up of the first ten hundred most-used words of the language.
"""

# REMOVE THIS IN REGULAR COGS:
# pylint: disable=unused-import

import asyncio
import logging
import math

import discord

from futaba import permissions
from futaba.cogs.abc import AbstractCog
from futaba.exceptions import CommandFailed

logger = logging.getLogger(__name__)


class SimplewriterCog(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.bot.add_listener(self.on_message, "on_message")
        self.bot.add_listener(self.on_message_edit, "on_message_edit")
        self.journal = bot.get_broadcaster("/simplewriter")

    def setup(self):
        pass

    def __unload(self):
        self.bot.remove_listener(self.on_message, "on_message")
        self.bot.remove_listener(self.on_message_edit, "on_message_edit")

    async def on_message(cog, message):
        if message.author.id == cog.bot.user.id:
            return
        await message.channel.send(message.id)

    async def on_message_edit(cog, before, after):
        pass
