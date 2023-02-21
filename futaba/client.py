#
# client.py
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
Contains the bot's discord client and the necessary handling functionality.
"""

import asyncio
import logging
import os
import sys
import traceback
from collections import deque
from datetime import datetime
from io import BytesIO

import aiohttp
import discord
from discord.ext import commands

from .cogs.journal import Journal
from .cogs.navi import Navi
from .cogs.reloader import Reloader
from .config import Configuration
from .converters.annotations import ANNOTATIONS
from .delayed import DelayedQueue
from .enums import Reactions
from .exceptions import (
    CommandFailed,
    InvalidCommandContext,
    ManualCheckFailure,
    SendHelp,
)
from .help import HelpCommand
from .journal import Broadcaster, LoggingOutputListener
from .lru import LruCache
from .punishment import PunishmentHandler
from .sql import SqlHandler
from .str_builder import StringBuilder
from .unicode import unicode_repr
from .utils import plural, user_discrim

logger = logging.getLogger(__name__)


def ignore_command_hooks(ctx):
    if ctx.command is None:
        return False

    if ctx.command.module == "discord.ext.commands.help":
        logger.debug("Ignoring normal command hooks for %r", ctx.command)
        return True

    return False


class Bot(commands.AutoShardedBot):
    __slots__ = (
        "config",
        "start_time",
        "journal_cog",
        "reloader_cog",
        "sql",
        "punish",
        "error_channel",
        "message_locks",
        "completed_commands",
        "queue",
    )

    def __init__(self, config: Configuration):
        self.config = config
        self.start_time = datetime.utcnow()
        self.journal_cog = None
        self.reloader_cog = None
        self.sql = SqlHandler(config.database_url)
        self.punish = PunishmentHandler(self)
        self.error_channel = None
        self.message_locks = LruCache(20)
        self.completed_commands = deque(maxlen=20)
        self.queue = DelayedQueue(config)

        super().__init__(
            command_prefix=self.my_command_prefix,
            description="futaba - A discord mod bot",
            max_messages=100_000,
            fetch_offline_members=True,
            intents=discord.Intents.all(),
        )

        self.help_command = HelpCommand()

    @staticmethod
    def my_command_prefix(bot, message):
        prefix = bot.prefix(message.guild)
        return commands.when_mentioned_or(prefix)(bot, message)

    def prefix(self, guild):
        if guild is None:
            return ""

        prefix = self.sql.settings.get_prefix(guild)
        return prefix or self.config.default_prefix

    @property
    def uptime(self):
        """Gets the bot's uptime"""

        return datetime.utcnow() - self.start_time

    def run_with_token(self):
        """
        Replace discord clients run command to include token from config
        If the token is empty or incorrect raises LoginError
        """

        if not self.config.token:
            logger.critical(
                "Token is empty. Please open the config file and add the bot's token!"
            )
            sys.exit(1)
        else:
            self.run(self.config.token)

    async def on_ready(self):
        """
        After the bot has logged in and filled up its cache.
        Sets up the bot's state, loads cogs then prints a 'ready' message.
        """

        # Get error channel
        if self.config.error_channel_id:
            channel = self.get_channel(self.config.error_channel_id)
            if isinstance(channel, discord.TextChannel):
                self.error_channel = channel

        # Setup mandatory cogs
        self.add_cog(Journal(self))
        logger.info("Loaded mandatory cog: Journal")

        self.add_cog(Navi(self))
        logger.info("Loaded mandatory cog: Navi")

        self.add_cog(Reloader(self))
        logger.info("Loaded mandatory cog: Reloader")

        def _cog_ok(cog):
            # Special files
            if cog.startswith("_"):
                return False

            # Check for mandatory cogs
            if cog in Reloader.MANDATORY_COGS:
                return False

            # Cog is a directory
            return os.path.isdir(f"futaba/cogs/{cog}")

        files = [cog for cog in os.listdir("futaba/cogs") if _cog_ok(cog)]
        logger.info("Cogs found: %s", ", ".join(files))

        # Load cogs
        for file in files:
            try:
                self.load_extension(f"futaba.cogs.{file}")
            except Exception as error:
                # Something made the loading fail
                # So log it with reason and tell user to check it
                logger.error("Load failed: %s", file, exc_info=error)
                sys.exit(1)
            else:
                logger.info("Loaded cog: %s", file)

        # Register logger to catch journal events
        listener = LoggingOutputListener(self.journal_cog.router, "/")
        self.journal_cog.router.register(listener)

        # Performing migrations
        self.sql.guilds.migrate(self)

        # Initialize cog databases
        for cog in self.get_cogs():
            cog.setup()

        # Start processing backlogged events
        self.queue.start(self.loop)

        # Finished
        pyver = sys.version_info
        logger.info("Powered by Python %d.%d.%d", pyver.major, pyver.minor, pyver.micro)
        logger.info("Using discord.py %s", discord.__version__)
        logger.info("Logged in as %s (%d)", self.user.name, self.user.id)
        logger.info("Connected to:")
        logger.info("* %d guild%s", len(self.guilds), plural(len(self.guilds)))
        logger.info("* %d channels", sum(1 for _ in self.get_all_channels()))
        logger.info("* %d users", len(self.users))
        logger.info("------")
        logger.info("Ready!")

    def get_broadcaster(self, root):
        """
        A utility method for instantiating a bound Broadcaster on the given path.
        """

        return Broadcaster(self.journal_cog.router, root)

    def add_tasks(self, *tasks):
        logger.info("Adding tasks to database and to asyncio event loop")
        assert tasks

        with self.sql.transaction():
            for task in tasks:
                self.sql.navi.add_task(task)

        # Put on event loop only after the database has successfully committed
        for task in tasks:
            task.execute_later()

    def get_cogs(self):
        return filter(None, map(self.get_cog, self.cogs))

    async def on_guild_join(self, guild):
        """
        Event for handling joining a new guild.
        Adds it to the database for triggering guild migration in the database.
        """

        logger.info("Guild join event for '%s' (%d)", guild.name, guild.id)
        with self.sql.transaction():
            self.sql.guilds.activate_guild(guild)

    async def on_guild_remove(self, guild):
        """
        Event for handling leaving a guild.
        Removes it to the database for triggering guild migration in the database.
        """

        logger.info("Guild leave event for '%s' (%d)", guild.name, guild.id)
        with self.sql.transaction():
            self.sql.guilds.deactivate_guild(guild)

    def message_lock(self, message):
        return self.message_locks.get_or_put(message, asyncio.Lock)

    async def on_command(self, ctx):
        """
        Handles pre-command instructions, such as adding the "wait" reaction.
        """

        if ignore_command_hooks(ctx):
            return

        self.loop.create_task(self._add_waiting(ctx.message))

    async def _add_waiting(self, message):
        await asyncio.sleep(0.5)

        async with self.message_lock(message):
            if message not in self.completed_commands:
                await Reactions.WAITING.add(message)

    async def on_command_completion(self, ctx):
        """
        Handles successful commands.
        Adds the success reaction and removes all others.
        """

        async with self.message_lock(ctx.message):
            try:
                if isinstance(ctx.channel, discord.abc.GuildChannel):
                    await ctx.message.clear_reactions()

                await Reactions.SUCCESS.add(ctx.message)
                self.completed_commands.append(ctx.message)
            except discord.NotFound:
                pass

    async def on_command_error(self, ctx, error):
        """
        Handles errors when a command raises an exception.
        Some exceptions are "normal", such as CommandFailed or MissingRequiredArgument.
        """

        # Complains about "context" vs "ctx"
        # pylint: disable=arguments-differ

        if ignore_command_hooks(ctx):
            return

        async with self.message_lock(ctx.message):
            try:
                if isinstance(ctx.channel, discord.abc.GuildChannel):
                    await ctx.message.clear_reactions()

                await self.handle_error(ctx, error)
                self.completed_commands.append(ctx.message)
            except discord.NotFound:
                pass

    async def handle_error(self, ctx, error):
        if isinstance(error, commands.errors.CommandNotFound):
            # Ignore no command found as we don't care if it wasn't one of our commands
            pass

        elif isinstance(error, commands.errors.MissingRequiredArgument):
            # Tell the user they are missing a required argument
            logger.info("User was missing required argument for command")

            # Create the embed to tell user what argument is missing
            embed = discord.Embed(colour=discord.Colour.red())
            embed.title = "Required argument missing"
            embed.add_field(name="Argument", value=error.param.name)

            # Convert the annotation to be more readable
            annotation = ANNOTATIONS[error.param.annotation.__name__]
            embed.add_field(name="Annotation", value=annotation)

            await asyncio.gather(
                ctx.send(embed=embed), Reactions.MISSING.add(ctx.message)
            )

        elif isinstance(
            error, (commands.errors.BadArgument, commands.errors.BadUnionArgument)
        ):
            # Tell the user they couldn't find what they were looking for
            logger.info("User specified argument that does not compute")

            # Create the embed to tell user what argument was invalid
            embed = discord.Embed(colour=discord.Colour.red())
            embed.title = "Unable to retrieve argument"
            embed.description = str(error)

            await asyncio.gather(
                ctx.send(embed=embed), Reactions.MISSING.add(ctx.message)
            )

        elif isinstance(error, (commands.errors.CheckFailure, discord.Forbidden)):
            # Tell the user they don't have the permission to tun the command
            logger.info("Permission check for command failed")
            await Reactions.DENY.add(ctx.message)

        elif isinstance(error, ManualCheckFailure):
            # Tell the user they don't have permission and report the error message if any
            logger.info("Manual permission check for command failed")

            if error.kwargs:
                await ctx.send(**error.kwargs)

            await Reactions.DENY.add(ctx.message)

        elif isinstance(error, CommandFailed):
            # The command failed, report the error message (if any) and send the FAIL reaction
            logger.info("Command failed, sending output: %r", error.kwargs)

            if error.kwargs:
                await ctx.send(**error.kwargs)

            await Reactions.FAIL.add(ctx.message)

        elif isinstance(error, InvalidCommandContext):
            # Explicitly ignore, this command was not even meant to be invoked in the first place
            # This is sent when we explicitly DO NOT want to add a SUCCESS reaction
            pass

        elif isinstance(error, SendHelp):
            logger.info("Manually sending help for command")
            await Reactions.HELP.add(ctx.message)

        elif isinstance(error, commands.errors.CommandInvokeError):
            logger.debug("Handling CommandInvokeError...")
            error = error.__cause__

            if isinstance(error, aiohttp.ClientError):
                logger.error("Unexpected aiohttp client error", exc_info=error)
                trace, filename = self.get_traceback(error)
                embed = discord.Embed(colour=discord.Colour.dark_red())
                embed.set_author(name="Spurious network error")
                descr = StringBuilder()
                descr.writeln("Traceback has been posted to developer's error channel.")
                error_str = str(error)
                if error_str:
                    descr.writeln(f"```py\n{error_str}\n```")
                embed.description = str(descr)
                await asyncio.gather(
                    ctx.send(embed=embed),
                    self.upload_traceback(ctx, trace, filename),
                    Reactions.NETWORK.add(ctx.message),
                )

            else:
                # Other exception, probably not meant to happen. Send it as an embed.
                await self.report_other_exception(
                    ctx, error, "Unexpected error occurred!"
                )

        elif isinstance(error, commands.errors.ExpectedClosingQuoteError):
            logger.info("User is missing closing quote for command")

            # Create the embed to tell the user that they are missing a closing quote
            embed = discord.Embed(colour=discord.Colour.red())
            embed.title = "Closing quote missing"

            await asyncio.gather(
                ctx.send(embed=embed), Reactions.MISSING.add(ctx.message)
            )

        else:
            logger.error("Unknown discord command error raised", exc_info=error)
            await self.report_other_exception(
                ctx, error, "Unwrapped exception was raised from command!"
            )

    async def report_other_exception(self, ctx, error, title):
        logger.error("Unexpected error during command!", exc_info=error)
        anger_emoji = self.get_emoji(self.config.anger_emoji_id) or "\N{ANGER SYMBOL}"
        trace, filename = self.get_traceback(error)

        # Send traceback to error channel, if it exists
        if self.error_channel is not None:
            await self.upload_traceback(ctx, trace, filename)

        # Output exception information
        embed = discord.Embed(colour=discord.Colour.red())
        embed.title = f"{anger_emoji} {title}"

        if len(trace) > 1700:
            embed.description = (
                "Error output too long, see attached file. "
                "\N{WHITE UP POINTING BACKHAND INDEX}"
            )
            data = BytesIO(trace.encode("utf-8"))
            file = discord.File(fp=data, filename=filename)
        else:
            embed.description = f"```py\n{trace}\n```"
            file = None

        await asyncio.gather(
            ctx.send(embed=embed, file=file), Reactions.FAIL.add(ctx.message)
        )

    @staticmethod
    def get_traceback(error):
        trace = "\n".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        unix_time = int(datetime.now().timestamp())
        filename = f"futaba-traceback-{unix_time}.log"
        return trace, filename

    async def upload_traceback(self, ctx, trace, filename):
        logger.info(
            "Uploading '%s' to #%s (%d)",
            filename,
            self.error_channel.name,
            self.error_channel.id,
        )

        # Write context information to traceback
        full_tb = StringBuilder()
        full_tb.writeln(f"Timestamp: {datetime.now()}")
        full_tb.writeln(f"User: {user_discrim(ctx.author)} ({ctx.author.id})")
        full_tb.writeln(f"Command: {ctx.command}")
        full_tb.writeln(f"  Signature: {ctx.command.signature}")
        full_tb.writeln(f"  Prefix: {ctx.prefix}")
        full_tb.writeln(f"  Cog name: {ctx.command.cog_name}")
        full_tb.writeln(f"Message: ({ctx.message.id})")
        full_tb.writeln(f"  Content: {unicode_repr(ctx.message.content)}")
        full_tb.writeln("  Arguments:")
        for arg in ctx.args:
            full_tb.writeln(f"    {arg!r}")
        if not ctx.args:
            full_tb.writeln("    (none)")

        full_tb.writeln("  Keyword arguments:")
        for key, arg in ctx.kwargs.items():
            full_tb.writeln(f"    {key} = {arg!r}")
        if not ctx.kwargs:
            full_tb.writeln("    (none)")

        if isinstance(ctx.channel, discord.DMChannel):
            full_tb.writeln(f"Channel: DM ({ctx.channel.id})")
        elif isinstance(ctx.author, discord.Member):
            full_tb.writeln(f"Guild: {ctx.guild.name} ({ctx.guild.id})")
            full_tb.writeln(f"Channel: #{ctx.channel.name} ({ctx.channel.id})")
            full_tb.writeln("Permissions:")
            perms = self.error_channel.permissions_for(ctx.author)
            for perm, value in perms:
                full_tb.writeln(f"  {'HAS  ' if value else 'LACKS'} {perm}")

            full_tb.writeln("Permission overwrites:")
            perms = self.error_channel.overwrites_for(ctx.author)
            for perm, value in perms:
                if value is None:
                    setting = "N/A  "
                elif value is True:
                    setting = "ALLOW"
                elif value is False:
                    setting = "DENY "
                else:
                    raise ValueError(f"Invalid permission value: {value!r}")
                full_tb.writeln(f"  {setting} {perm}")

            full_tb.writeln("Roles:")
            for role in ctx.author.roles:
                perms = role.permissions.value
                full_tb.writeln(f"  {role.name} ({role.id}):")
                full_tb.writeln(f"    created at: {role.created_at}")
                full_tb.writeln(f"    members: {len(role.members)}")
                full_tb.writeln(f"    permissions: 0x{perms:016x}")

        # Write actual traceback
        full_tb.writeln()
        full_tb.writeln(trace)

        # Upload traceback to error channel
        unix_time = int(datetime.now().timestamp())
        filename = f"futaba-extended-traceback-{unix_time}.log"
        file = discord.File(fp=full_tb.bytes_io(), filename=filename)
        await self.error_channel.send(file=file)
