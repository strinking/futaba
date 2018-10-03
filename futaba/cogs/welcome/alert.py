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

import logging
from collections import defaultdict

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import JoinAlertKey, ValueRelationship
from futaba.exceptions import ManualCheckFailure, SendHelp
from futaba.str_builder import StringBuilder
from futaba.unicode import normalize_caseless

logger = logging.getLogger(__package__)

__all__ = ["JoinAlert", "Alert"]


class JoinAlert:
    __slots__ = ("key", "op", "value")

    def __init__(self, key, op, value):
        self.key = key
        self.op = op
        self.value = value

    def matches(self, member):
        value = self.value
        member_value = getattr(member, self.attr)
        if isinstance(self.value, str) and isinstance(member_value, str):
            value = normalize_caseless(value)
            member_value = normalize_caseless(member_value)
        return self.op.comparator(member_value, value)

    @property
    def attr(self):
        return self.key.value

    def __str__(self):
        return f"{self.key.display_name} {self.op.symbol} {self.value}"


class Alert:
    __slots__ = ("bot", "journal", "alerts")

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster("/welcome/alert")
        self.alerts = defaultdict(dict)

        for guild in bot.guilds:
            alert_parts = bot.sql.welcome.get_all_alerts(guild)
            for key, op, value in alert_parts:
                alert = JoinAlert(key, op, value)
                self.alerts[guild][key] = alert

    async def member_join(self, member):
        logger.info("Member '%s' (%d) joined, checking alerts.", member.name, member.id)
        for alert in self.alerts[member.guild].values():
            if alert.matches(member):
                logger.info("Matches alert: %s!", alert)
                content = f"Member {member.mention} violates alert: {alert}"
                self.journal.send("", member.guild, content, icon="found")

    @commands.group(name="joinalert", aliases=["jalert"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert(self, ctx):
        """ Manages the welcome cog for managing new users and roles. """

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @alert.command(name="show", aliases=["display", "list"])
    @commands.guild_only()
    async def alert_show(self, ctx):
        """ Lists all join alerts for this guild. """

        logging.info(
            "Showing all join alerts for '%s' (%d)", ctx.guild.name, ctx.guild.id
        )

        embed = discord.Embed()
        embed.set_author(name="Join alerts")
        descr = StringBuilder()

        for alert in self.alerts[ctx.guild].values():
            descr.writeln(f"- `{alert}`")

        if descr:
            embed.colour = discord.Colour.dark_teal()
            embed.description = str(descr)
        else:
            embed.colour = discord.Colour.dark_purple()
            embed.description = "No alerts for this guild"

        await ctx.send(embed=embed)

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
            raise ManualCheckFailure(content=f"Invalid attribute: {attribute}")

        try:
            op = ValueRelationship(relationship)
        except ValueError:
            raise ManualCheckFailure(content=f"Invalid relationship: {relationship}")

        try:
            value = key.parse_value(amount)
        except ValueError as error:
            raise ManualCheckFailure(content=str(error))

        alert = JoinAlert(key, op, value)
        logging.info("Adding join alert: %s", alert)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.add_alert(ctx.guild, alert)

        self.alerts[ctx.guild][key] = alert

        # Notify the user
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Successfully added join alert")
        descr = StringBuilder()
        descr.writeln(f"- `{alert}`")
        descr.writeln(
            "To get these notifications in a channel, add a logger for path `/welcome/alert`"
        )
        embed.description = str(descr)

        await ctx.send(embed=embed)

    @alert.command(name="remove", aliases=["rm", "delete", "del"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert_remove(self, ctx, attribute: str):
        """
        If there exists a join alert tracking the given attribute, delete it.

        Possible attributes: id, created, name, discrim, avatar, status
        """

        logging.info(
            "Got request to delete join alert for '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        try:
            key = JoinAlertKey.parse(attribute)
        except ValueError:
            raise ManualCheckFailure(content=f"Invalid attribute: {attribute}")

        logging.info("Removing join alert: %s", key)
        with self.bot.sql.transaction():
            self.bot.sql.welcome.remove_alert(ctx.guild, key)

        self.alerts[ctx.guild].pop(key, None)
