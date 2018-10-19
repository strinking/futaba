#
# cogs/navi/core.py
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
Mandatory cog that adds navi, futaba's helpful assistant. It is useful for
persistently storing and managing scheduled tasks.
"""

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.exceptions import CommandFailed
from .task import navi_task_factory
from .scheduler import NaviScheduler

logger = logging.getLogger(__name__)


class Navi:
    __slots__ = ("bot", "journal", "scheduler")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/navi")
        self.scheduler = NaviScheduler()

        for guild in bot.guilds:
            raw_tasks = bot.sql.navi.get_tasks()
