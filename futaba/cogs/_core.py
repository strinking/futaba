#
# cogs/<cog folder name>/core.py
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
<description>
"""

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.exceptions import CommandFailed
from ..abc import AbstractCog

logger = logging.getLogger(__name__)


class NameOfCog(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/A PATH THAT MAKES SENSE FOR THIS COG")

    def setup(self):
        # Fetching information from the database for this cog
        pass
