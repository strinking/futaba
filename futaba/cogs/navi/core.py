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
from datetime import datetime

import dateparser
import discord
from discord.ext import commands

from futaba import permissions
from futaba.exceptions import CommandFailed
from futaba.utils import escape_backticks, fancy_timedelta
from .task import SendMessageTask, build_navi_task
from .scheduler import NaviScheduler

logger = logging.getLogger(__name__)


class Navi:
    __slots__ = ("bot", "journal", "scheduler")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/navi")
        self.scheduler = NaviScheduler()

        raw_tasks = bot.sql.navi.get_tasks()
        for raw_task in raw_tasks:
            try:
                task = build_navi_task(bot, raw_task)
                self.scheduler.add(task)
            except ValueError as error:
                logger.warning("Error while loading task from database", exc_info=error)

        asyncio.create_task(self.scheduler.main_loop())

    def add_tasks(self, *tasks):
        logger.info("Adding tasks to database and Navi scheduler, ids: %s", ", ".join(str(task.id) for task in tasks))

        with self.bot.sql.transaction():
            for task in tasks:
                self.bot.sql.navi.add_task(task)

        for task in tasks:
            self.scheduler.add(task)

    @commands.command(name="remind", aliases=["remindme", "alarm"])
    async def remind_me(self, ctx, when: str, message: str):
        """ Request the bot remind you in the given time. """

        timestamp = dateparser.parse(when)
        now = datetime.now()
        if timestamp is None:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = f"Unknown date specification: `{escape_backticks(when)}`"
            raise CommandFailed(embed=embed)
        elif timestamp < now:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = f"Specified date was in the past"
            raise CommandFailed(embed=embed)

        logger.info("Creating self-reminder SendMessageTask for '%s' (%d): %r",
                ctx.author.name, ctx.author.id, message)

        # Create navi task
        time_since = fancy_timedelta(timestamp - now)
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Reminder!")
        embed.description = f"{time_since} ago, you were asked to be reminded of:\n{message}"
        embed.timestamp = now
        self.add_tasks(SendMessageTask(None, ctx.author, timestamp, None, ctx.author, embed=embed))
