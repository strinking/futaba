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
import logging
import math

import discord
from discord.ext import commands

from futaba import permissions
from futaba.cogs.abc import AbstractCog
from futaba.exceptions import CommandFailed

logger = logging.getLogger(__name__)


class StatbotCog(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/statbot")

    def setup(self):
        # Fetching information from the database for this cog
        pass
