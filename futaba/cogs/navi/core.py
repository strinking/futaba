#
# cogs/navi/core.py
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
Mandatory cog that adds navi, futaba's helpful assistant. It is useful for
persistently storing and managing scheduled tasks.
"""

import logging
from datetime import datetime, timedelta

import dateparser
import discord
from discord.ext import commands

from futaba.exceptions import CommandFailed
from futaba.navi import SendMessageTask, build_navi_task
from futaba.str_builder import StringBuilder
from futaba.utils import escape_backticks, fancy_timedelta
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

MAX_REMINDER_DURATION = timedelta(days=365)


class Navi(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/navi")

    def setup(self):
        raw_tasks = self.bot.sql.navi.get_tasks()
        for raw_task in raw_tasks.values():
            try:
                task = build_navi_task(self.bot, raw_task)
                task.execute_later()
            except ValueError as error:
                logger.warning(
                    "Error while loading or running task from database", exc_info=error
                )

    @commands.command(name="remind", aliases=["reminder", "remindme", "alarm"])
    async def remind_me(self, ctx, when: str, *, message: str):
        """Request the bot remind you in the given time."""

        timestamp = dateparser.parse(when)
        now = datetime.now()
        if timestamp is None:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                f"Unknown date specification: `{escape_backticks(when)}`"
            )
            raise CommandFailed(embed=embed)

        if now > timestamp:
            # First, try to see if a naive time specification put it in the past
            new_timestamp = dateparser.parse(f"in {when}")
            if new_timestamp is None or now > new_timestamp:
                time_since = fancy_timedelta(now - timestamp)
                embed = discord.Embed(colour=discord.Colour.red())
                embed.description = f"Specified date was in the past: {time_since} ago"
                raise CommandFailed(embed=embed)

            # Was successful, replace it
            timestamp = new_timestamp

        # Check time
        assert timestamp > now
        duration = timestamp - now
        time_since = fancy_timedelta(duration)
        if duration > MAX_REMINDER_DURATION:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = f"Specified date is too far away: {time_since}"
            raise CommandFailed(embed=embed)

        logger.info(
            "Creating self-reminder SendMessageTask for '%s' (%d): %r",
            ctx.author.name,
            ctx.author.id,
            message,
        )

        # Create navi task
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name=f"Reminder made {time_since} ago")
        embed.description = f"You asked to be reminded of:\n\n{message}"
        embed.timestamp = now
        self.bot.add_tasks(
            SendMessageTask(
                self.bot,
                None,
                ctx.author,
                timestamp,
                None,
                ctx.author,
                embed=embed,
                metadata={"type": "reminder", "message": message},
            )
        )

    @commands.command(
        name="reminders", aliases=["reminds", "lreminder", "lremind", "alarms"]
    )
    async def remind_list(self, ctx):
        """Lists all reminders for the current user."""

        reminders = self.bot.sql.navi.get_reminders(ctx.author)
        if reminders:
            descr = StringBuilder()
            for reminder in reminders:
                until = fancy_timedelta(reminder.timestamp)
                message = escape_backticks(reminder.message)
                descr.writeln(
                    f"ID: #`{reminder.id:05}`: in `{until}` with message: `{message}`"
                )

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.set_author(name=f"Reminders for {ctx.author.display_name}")
            embed.description = str(descr)
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = f"No reminders for {ctx.author.mention}"

        await ctx.send(embed=embed)
