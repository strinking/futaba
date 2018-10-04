#
# cogs/<cog folder name>/core.py
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
<description>
"""

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.exceptions import CommandFailed

logger = logging.getLogger(__package__)


class NameOfCog:
    __slots__ = ("bot", "journal")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/A PATH THAT MAKES SENSE FOR THIS COG")
