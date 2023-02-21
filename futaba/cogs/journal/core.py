#
# cogs/journal/core.py
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
Cog for configuring Futaba journalling output, directing certain kinds
of messages to different logging channels.
"""

import asyncio
import json
import logging
import traceback
from itertools import islice
from pprint import pformat

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import TextChannelConv, UserConv
from futaba.exceptions import CommandFailed, SendHelp
from futaba.journal import ChannelOutputListener, DirectMessageListener, Router
from futaba.str_builder import StringBuilder
from futaba.utils import user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Journal"]


class Journal(AbstractCog):
    __slots__ = ("router", "journal")

    def __init__(self, bot):
        super().__init__(bot)
        bot.journal_cog = self
        self.router = Router(bot)
        self.journal = bot.get_broadcaster("/journal")

    def setup(self):
        logger.info("Loading journal output channels from the database")
        with self.bot.sql.transaction():
            for guild in self.bot.guilds:
                for output in self.bot.sql.journal.fetch_journal_channels(guild):
                    logger.info(
                        "Registering journal channel #%s (%d) for path '%s'",
                        output.sink.name,
                        output.sink.id,
                        output.path,
                    )
                    self.router.register(
                        ChannelOutputListener(self.router, output.path, output.sink)
                    )
                for output in self.bot.sql.journal.fetch_journal_users(self.bot, guild):
                    logger.info(
                        "Registering journal DM on user '%s' (%d) for path '%s'",
                        output.sink.name,
                        output.sink.id,
                        output.path,
                    )
                    self.router.register(
                        DirectMessageListener(self.router, output.path, output.sink)
                    )
        self.router.start(self.bot.loop)

    @commands.group(name="journal", aliases=["log"])
    async def log(self, ctx):
        """Configure channel output for bot journal events."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @log.command(name="show", aliases=["display", "list"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_show(self, ctx, *channels: TextChannelConv):
        """
        Displays current settings for this guild.
        If channels are provided, then only outputs for those channels are fetched.
        """

        if not channels:
            channels = ctx.guild.channels

        outputs = self.bot.sql.journal.get_journals_on_channels(*channels)
        outputs = sorted(outputs, key=lambda out: out.path)
        attributes = []
        descr = StringBuilder()

        for output in outputs:
            if not output.settings.recursive:
                attributes.append("exact path")

            attr_str = f'({", ".join(attributes)})' if attributes else ""
            descr.writeln(
                f"- `{output.path}` mounted at {output.sink.mention} {attr_str}"
            )
            attributes.clear()

        if outputs:
            embed = discord.Embed(colour=discord.Colour.teal(), description=str(descr))
            embed.set_author(name="Current journal outputs")
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No journal outputs!")

        await ctx.send(embed=embed)

    def log_updated_message(self, location):
        if isinstance(location, discord.TextChannel):
            outputs = list(self.bot.sql.journal.get_journals_on_channels(location))
        elif isinstance(location, discord.abc.User):
            outputs = list(self.bot.sql.journal.get_journals_on_user(location))
        else:
            raise TypeError(f"Unknown location type: {location!r}")

        if outputs:
            paths = " ".join(f"`{output.path}`" for output in outputs)
        else:
            paths = "(none)"

        return f"Journal outputs updated! Current paths: {paths}"

    @staticmethod
    def get_flags(flags):
        recursive = True
        for flag in flags:
            if flag == "-exact":
                recursive = False
            else:
                raise CommandFailed(content=f"No such flag: `{flag}`")

        return recursive

    @log.command(name="add", aliases=["append", "extend", "new", "set", "update"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_add(self, ctx, path: str, channel: TextChannelConv, *flags: str):
        """
        Add a journal logger to the channel for the given path.
        Accepts the optional flags:
            -exact, Don't recursively accept journal events from children.
        """

        logger.info(
            "Adding journal logger for channel #%s (%d) on path '%s'",
            channel.name,
            channel.id,
            path,
        )

        recursive = self.get_flags(flags)

        logger.debug("Registering route")
        self.router.register(ChannelOutputListener(self.router, path, channel))

        logger.debug("Updating database for channel output")
        with self.bot.sql.transaction():
            journal_sql = self.bot.sql.journal
            if journal_sql.has_journal_channel(channel, path):
                journal_sql.update_journal_output(ctx.guild, channel, path, recursive)
            else:
                journal_sql.add_journal_output(ctx.guild, channel, path, recursive)

        await channel.send(content=self.log_updated_message(channel))
        content = f"Added journal logger to {channel.mention} for `{path}`"
        self.journal.send(
            "channel/add",
            ctx.guild,
            content,
            icon="journal",
            channel=channel,
            path=path,
            recursive=recursive,
        )

    @log.command(name="remove", aliases=["rm", "delete", "del"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_remove(self, ctx, path: str, channel: TextChannelConv):
        """
        Removes a journal logger for the given path from the channel.
        """

        logger.info(
            "Removing journal logger for channel #%s (%d) from path '%s'",
            channel.name,
            channel.id,
            path,
        )

        listener = self.router.get(path, channel=channel)
        if listener is None:
            # No listener found
            raise CommandFailed(
                content=f"No output on `{path}` found for {channel.mention}"
            )

        self.router.unregister(listener)

        with self.bot.sql.transaction():
            self.bot.sql.journal.delete_journal_output(ctx.guild, channel, path)

        await channel.send(content=self.log_updated_message(channel))
        content = f"Removed journal logger to {channel.mention} for `{path}`"
        self.journal.send(
            "channel/remove",
            ctx.guild,
            content,
            icon="journal",
            channel=channel,
            path=path,
        )

    @log.command(name="rename", aliases=["rn", "move", "mv"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_rename(
        self,
        ctx,
        old_channel: TextChannelConv,
        new_channel: TextChannelConv,
        path: str,
        *flags: str,
    ):
        """
        Moves a journal logger from one channel to another.
        Accepts the optional flags:
            -exact, Don't recursively accept journal events from children.
        """

        logger.info(
            "Moving journal logger from channel #%s (%d) to #%s (%d) for path '%s'",
            old_channel.name,
            old_channel.id,
            new_channel.name,
            new_channel.id,
            path,
        )

        recursive = self.get_flags(flags)

        listener = self.router.get(path, channel=old_channel)
        if listener is None:
            # No listener found at old channel
            raise CommandFailed(
                content=f"No output on `{path}` found for {old_channel.mention}"
            )

        listener.channel = new_channel

        logger.debug("Updating database for moved channel output")
        with self.bot.sql.transaction():
            self.bot.sql.journal.delete_journal_output(ctx.guild, old_channel, path)
            self.bot.sql.journal.add_journal_output(
                ctx.guild, new_channel, path, recursive
            )

        await asyncio.gather(
            old_channel.send(content=self.log_updated_message(old_channel)),
            new_channel.send(content=self.log_updated_message(new_channel)),
        )

        content = f"Moved journal logger from {old_channel.mention} to {new_channel.mention} for `{path}`"
        self.journal.send(
            "channel/move",
            ctx.guild,
            content,
            icon="journal",
            old_channel=old_channel,
            new_channel=new_channel,
            path=path,
            recursive=recursive,
        )

    @log.command(name="send", aliases=["broadcast"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_send(self, ctx, path: str, content: str, *attributes: str):
        """
        Manually send a journal event to test logging channels.
        The content must be a single argument, wrapped in quotes if
        it has spaces, and you can specify a number of journal attributes
        in the form KEY=VALUE.
        """

        if path == "/":
            raise CommandFailed(content="Cannot broadcast on /")

        journal_attributes = {}
        for attribute in attributes:
            try:
                key, value = attribute.split("=")
                journal_attributes[key] = value
            except ValueError:
                raise CommandFailed(
                    content="All attributes must be in the form KEY=VALUE"
                )

        logger.info(
            "Sending manual journal event: '%s' (attrs: %s)",
            content,
            journal_attributes,
        )
        self.bot.get_broadcaster(path).send(
            "", ctx.guild, content, **journal_attributes
        )

    @log.group(name="dm", aliases=["pm"])
    async def log_dm(self, ctx):
        """Configure direct messages for bot journal events."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @log_dm.command(name="show", aliases=["display", "list"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_dm_show(self, ctx, user: UserConv = None):
        """
        Displays current journal mounts for a user.
        """

        if user is None:
            user = self.bot.get_user(ctx.author.id)
        else:
            user = self.bot.get_user(user.id)

        outputs = self.bot.sql.journal.get_journals_on_user(user)
        outputs = sorted(outputs, key=lambda out: out.path)
        attributes = []
        descr = StringBuilder(f"{user.mention}:\n\n")

        for output in outputs:
            if not output.settings.recursive:
                attributes.append("exact path")

            attr_str = f'({", ".join(attributes)})' if attributes else ""
            descr.writeln(f"- `{output.path}` {attr_str}")
            attributes.clear()

        if outputs:
            embed = discord.Embed(colour=discord.Colour.teal(), description=str(descr))
            embed.set_author(name="Current journal outputs")
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No journal outputs!")

        await ctx.send(embed=embed)

    @log_dm.command(name="add", aliases=["append", "extend", "new", "set", "update"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_dm_add(self, ctx, path: str, *flags: str):
        """
        Add a DM journal logger for the given path.
        Accepts the optional flags:
            -exact, Don't recursively accept journal events from children.
        """

        logger.info(
            "Adding journal logger for user '%s' (%d) on path '%s'",
            ctx.author.name,
            ctx.author.id,
            path,
        )

        recursive = self.get_flags(flags)

        logger.debug("Registering route")
        self.router.register(DirectMessageListener(self.router, path, ctx.author))

        logger.debug("Updating database for user output")
        user = self.bot.get_user(ctx.author.id)
        with self.bot.sql.transaction():
            journal_sql = self.bot.sql.journal
            if journal_sql.has_journal_user(user, path):
                journal_sql.update_journal_output(ctx.guild, user, path, recursive)
            else:
                journal_sql.add_journal_output(ctx.guild, user, path, recursive)

        await ctx.send(content=self.log_updated_message(user))
        content = f"Added journal logger to {user_discrim(ctx.author)} for `{path}`"
        self.journal.send(
            "user/add",
            ctx.guild,
            content,
            icon="journal",
            user=ctx.author,
            path=path,
            recursive=recursive,
        )

    @log_dm.command(name="remove", aliases=["rm", "delete", "del"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_dm_remove(self, ctx, path: str):
        """
        Removes a DM journal logger for the given path.
        """

        logger.info(
            "Removing journal logger for user '%s' (%d) from path '%s'",
            ctx.author.name,
            ctx.author.id,
            path,
        )

        user = self.bot.get_user(ctx.author.id)
        listener = self.router.get(path, user=user)
        if listener is None:
            # No listener found
            raise CommandFailed(
                content=f"No output on `{path}` found for {user_discrim(ctx.author)}"
            )

        self.router.unregister(listener)

        with self.bot.sql.transaction():
            self.bot.sql.journal.delete_journal_output(ctx.guild, user, path)

        await ctx.send(content=self.log_updated_message(user))
        content = f"Removed journal logger to {user_discrim(ctx.author)} for `{path}`"
        self.journal.send(
            "user/remove",
            ctx.guild,
            content,
            icon="journal",
            user=ctx.author,
            path=path,
        )

    def log_filter(self, guild, condition, max_items):
        logging.info(
            "Finding journal entries in guild '%s' (%d) matching: %s",
            guild.name,
            guild.id,
            condition or "(none)",
        )

        def create_scope(event):
            return {
                "path": str(event.path),
                "ppath": event.path,
                "guild": guild,
                "content": event.content,
                "attributes": event.attributes,
            }

        events = reversed(self.journal.history)
        events = filter(lambda evt: evt.guild == guild, events)
        events = islice(events, max_items)

        if condition is None:
            matched = events
        else:
            try:
                compile(condition, "<futaba journal-find eval>", "eval")
            except Exception as error:
                logger.info("Error compiling condition", exc_info=error)
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name="Compilation error parsing condition")
                trace = "\n".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
                embed.description = f"```py\n{trace}\n```"
                raise CommandFailed(embed=embed)

        matched = []
        error_embeds = []
        for event in tuple(events):
            try:
                # Limited eval for journal filter evaluation
                # pylint: disable=eval-used
                if eval(condition, create_scope(event)):
                    matched.append(event)
            except Exception as error:
                logger.info("Runtime error while evaluating condition", exc_info=error)

                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name="Runtime error checking condition")
                trace = "\n".join(
                    traceback.format_exception(type(error), error, error.__traceback__)
                )
                embed.description = f"```py\n{trace}\n```"
                error_embeds.append(embed)
        return matched, error_embeds

    @log.command(name="find", aliases=["search", "query", "recent", "history"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_find(self, ctx, *, condition: str = None):
        """
        List previous journal events that match the given conditions.
        The condition is a Python expression with no variables but
        the following attributes:

        path: str
        ppath: PurePath
        guild: discord.Guild
        content: str
        attributes: dict
        """

        events, error_embeds = self.log_filter(ctx.guild, condition, 10)

        if error_embeds:
            await ctx.send(embed=error_embeds[0])

        if events:
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.set_author(name="Matching journal events")
            descr = StringBuilder()

            embeds = []
            for event in events:
                descr.writeln(f"Path: `{event.path}`, Content: {event.content}")
                descr.writeln(f"Attributes: ```py\n{pformat(event.attributes)}\n```\n")
                if len(descr) > 1400:
                    embed.description = str(descr)
                    embeds.append(embed)
                    descr.clear()
                    embed = discord.Embed(colour=discord.Colour.dark_teal())
                    embed.set_author(name="Matched journal events")
            embed.description = str(descr)
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No matching journal entries")
            embeds = (embed,)

        for i, embed in enumerate(embeds):
            embed.set_footer(text=f"Page {i + 1}/{len(embeds)}")
            await ctx.send(embed=embed)

    @log.command(name="dump", aliases=["jsondump", "recentdump", "historydump"])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_dump(self, ctx, *, condition: str = None):
        """
        Dump previous journal events that match the given conditions to JSON.
        The condition is a Python expression with no variables but
        the following attributes:

        path: str
        ppath: PurePath
        guild: discord.Guild
        content: str
        attributes: dict
        """

        events, error_embeds = self.log_filter(ctx.guild, condition, 50)

        if error_embeds:
            await ctx.send(embed=error_embeds[0])

        buffer = StringBuilder()
        obj = [event.to_dict() for event in reversed(events)]
        json.dump(obj, buffer, ensure_ascii=True)
        file = discord.File(buffer.bytes_io(), filename="journal-events.json")

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = (
            "Uploaded journal events as JSON, see attached file. "
            "\N{WHITE UP POINTING BACKHAND INDEX}"
        )
        await ctx.send(embed=embed, file=file)
