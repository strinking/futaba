#
# cogs/settings/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Cog for all commands that change bot settings. It ensures persistence
of configured settings in between runs of the bot.
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions

logger = logging.getLogger(__name__)

__all__ = [
    'Settings',
]

class Settings:
    __slots__ = (
        'bot',
    )

    def __init__(self, bot):
        self.bot = bot

    # TODO
