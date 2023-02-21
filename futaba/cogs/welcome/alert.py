#
# cogs/welcome/alert.py
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
Cog for checking new members and seeing if they match a join alert
configured by staff. If so, a notification is sent to /welcome/alert.
"""

import logging
from itertools import islice

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import JoinAlertKey, ValueRelationship
from futaba.exceptions import CommandFailed, ManualCheckFailure, SendHelp
from futaba.str_builder import StringBuilder
from futaba.unicode import normalize_caseless
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["JoinAlert", "Alert"]


class JoinAlert:
    __slots__ = ("guild", "id", "key", "op", "value")

    def __init__(self, guild, id, key, op, value):
        self.guild = guild
        self.id = id
        self.key = key
        self.op = op
        self.value = value

    def setup(self):
        pass

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


class Alert(AbstractCog):
    __slots__ = ("journal", "alerts")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/welcome/alert")
        self.alerts = {}

        for guild in bot.guilds:
            alert_parts = bot.sql.welcome.get_all_alerts(guild)
            for id, key, op, value in alert_parts:
                alert = JoinAlert(guild, id, key, op, value)
                self.alerts[id] = alert

    def setup(self):
        pass

    async def member_join(self, member):
        logger.info("Member '%s' (%d) joined, checking alerts.", member.name, member.id)
        for alert in self.alerts.values():
            if alert.guild == member.guild:
                if alert.matches(member):
                    logger.info("Matches alert: %s!", alert)
                    content = (
                        f"Member {member.mention} triggerred join alert: `{alert}`"
                    )
                    self.journal.send("", member.guild, content, icon="found")

    @commands.group(name="joinalert", aliases=["jalert"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert(self, ctx):
        """Manages the welcome cog for managing new users and roles."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @alert.command(name="show", aliases=["display", "list"])
    @commands.guild_only()
    async def alert_show(self, ctx):
        """Lists all join alerts for this guild."""

        logging.info(
            "Showing all join alerts for '%s' (%d)", ctx.guild.name, ctx.guild.id
        )

        embed = discord.Embed()
        embed.set_author(name="Join alerts")
        descr = StringBuilder()
        descr.writeln("__Alert ID__ | __Condition__")

        for alert in self.alerts.values():
            assert alert.id is not None, "Alert was not given an ID"
            descr.writeln(f"#**`{alert.id:05}`** | `{alert}`")

        if self.alerts:
            embed.colour = discord.Colour.dark_teal()
            embed.description = str(descr)
        else:
            embed.colour = discord.Colour.dark_purple()
            embed.description = "No alerts for this guild"

        await ctx.send(embed=embed)

    @alert.command(name="match", aliases=["matches", "matching", "users", "members"])
    @commands.guild_only()
    async def alert_match(self, ctx, id: int):
        """
        Lists all members currently joined who matches the conditions given by the join alert ID.
        """

        logging.info(
            "Showing all members matching join alert %d in guild '%s' (%d)",
            id,
            ctx.guild.name,
            ctx.guild.id,
        )

        try:
            alert = self.alerts[id]
        except KeyError:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.set_author(name="Alert check failed")
            embed.description = f"No such join alert id: `{id}`"
            raise CommandFailed(embed=embed)

        embed = discord.Embed()
        embed.set_author(name="Matching members")
        descr = StringBuilder()
        descr.writeln(f"Join alert: `{alert}`")

        matching_members = list(filter(alert.matches, ctx.guild.members))
        if matching_members:
            embed.colour = discord.Colour.dark_teal()
            descr.writeln(f"Found {len(matching_members)} matching members:")
            descr.writeln()

            max_members = 8
            for member in islice(matching_members, 0, max_members):
                descr.writeln(f"- {member.mention}")
            if len(matching_members) > max_members:
                descr.writeln(f"... and {len(matching_members) - max_members} more")
        else:
            embed.colour = discord.Colour.dark_purple()
            descr.writeln("**No members matching this condition**")

        embed.description = str(descr)
        await ctx.send(embed=embed)

    @alert.command(name="add", aliases=["append", "extend"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert_add(self, ctx, attribute: str, relationship: str, *, amount: str):
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

        alert = JoinAlert(ctx.guild, None, key, op, value)
        logging.info("Adding join alert: %s", alert)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.add_alert(ctx.guild, alert)

        self.alerts[alert.id] = alert

        # Notify the user
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Successfully added join alert")
        descr = StringBuilder()
        descr.writeln(f"ID: #`{alert.id:05}`, Condition: `{alert}`")
        descr.writeln(
            "To get these notifications in a channel, add a logger for path `/welcome/alert`"
        )
        embed.description = str(descr)
        await ctx.send(embed=embed)

    @alert.command(name="remove", aliases=["rm", "delete", "del"])
    @commands.guild_only()
    @permissions.check_mod()
    async def alert_remove(self, ctx, id: int):
        """Delete the join alert with the given attribute."""

        logging.info(
            "Got request to delete join alert for '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        logging.info("Removing join alert for id: %d", id)
        with self.bot.sql.transaction():
            try:
                self.bot.sql.welcome.remove_alert(ctx.guild, id)
            except ValueError:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name="Deletion failed")
                embed.description = f"No such join alert id: `{id}`"
                raise CommandFailed(embed=embed)

        del self.alerts[id]
