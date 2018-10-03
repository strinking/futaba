#
# cogs/welcome/alert.py
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
Cog for checking new members and seeing if they match a join alert
configured by staff. If so, a notification is sent to /welcome/alert.
"""

import asyncio
import logging
from collections import defaultdict

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import JoinAlertKey, ValueRelationship
from futaba.exceptions import BadArgument, CommandFailed, SendHelp
from futaba.unicode import normalize_caseless

logger = logging.getLogger(__package__)

__all__ = ["JoinAlert", "Alert"]


class JoinAlert:
    __slots__ = ("key", "op", "value")

    def __init__(self, key, op, value):
        self.key = key
        self.op = op
        self.value = value

    def matches(self, member, value):
        member_value = getattr(member, self.key.value)
        if isinstance(value, str) and isinstance(member_value, str):
            value = normalize_caseless(value)
            member_value = normalize_caseless(member_value)
        return self.op.comparator(value, member_value)


class Alert:
    __slots__ = ("bot", "journal", "alerts")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/welcome")
        self.alerts = defaultdict(dict)

        for guild in bot.guilds:
            alert_parts = bot.sql.welcome.get_all_alerts(guild)
            for key, op, value in alert_parts:
                alert = JoinAlert(key, op, value)
                self.alerts[guild][key] = alert

    async def member_join(self, member):
        pass

    @commands.group(name="joinalert", aliases=["jalert"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert(self, ctx):
        """ Manages the welcome cog for managing new users and roles. """

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @alert.command(name="add", aliases=["append", "extend"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert_add(self, ctx, attribute: str, relationship: str, amount: str):
        """
        Adds a join alert with the given condition.

        Possible attributes: id, created, name, discrim, avatar, status
        Possible relationships: > >= = != < <= ~
        """

        logging.info(
            "Got request to add new join alert for '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        try:
            key = JoinAlertKey.parse(attribute)
        except ValueError:
            raise BadArgument(f"Invalid attribute: {key}")

        try:
            op = ValueRelationship(relationship)
        except ValueError:
            raise BadArgument(f"Invalid relationship: {relationship}")

        try:
            value = key.parse_value(amount)
        except ValueError as error:
            raise BadArgument(str(error))

        logging.info("Adding join alert: %s %s %s", attribute, relationship, amount)
        alert = JoinAlert(key, op, value)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.add_alert(ctx.guild, alert)

        self.alerts[ctx.guild] = alert

    # TODO list and remove
