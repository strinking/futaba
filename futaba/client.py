#
# client.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Holds the custom discord client
'''

import logging
import datetime
import os
import sys

import discord
from discord.ext import commands

from .cogs.journal import Journal
from .cogs.reloader import Reloader
from .config import Configuration
from .enums import Reactions
from .exceptions import CommandFailed, InvalidCommandContext, SendHelp
from .journal import Broadcaster, LoggingOutputListener
from .sql import SqlHandler
from .utils import plural

logger = logging.getLogger(__name__)

class Bot(commands.AutoShardedBot):
    __slots__ = (
        'config',
        'start_time',
        'journal_cog',
        'debug_chan',
        'sql',
    )

    def __init__(self, config: Configuration):
        self.config = config
        self.start_time = datetime.datetime.utcnow()
        self.journal_cog = None
        self.debug_chan = None
        self.sql = SqlHandler(config.database_url)

        super().__init__(command_prefix=self.command_prefix,
                         description='futaba - A discord mod bot',
                         pm_help=True)

    @staticmethod
    def command_prefix(bot, message):
        prefix = bot.prefix(message)
        return commands.when_mentioned_or(prefix)(bot, message)

    def prefix(self, message):
        if message.guild is None:
            return ''

        prefix = self.sql.settings.get_prefix(message.guild)
        return prefix or self.config.default_prefix

    @property
    def uptime(self):
        ''' Gets the bot's uptime '''

        return datetime.datetime.utcnow() - self.start_time

    def run_with_token(self):
        '''
        Replace discord clients run command to include token from config
        If the token is empty or incorrect raises LoginError
        '''

        if not self.config.token:
            logger.critical("Token is empty. Please open the config file and add the bot's token!")
            exit(1)
        else:
            self.run(self.config.token)

    async def on_ready(self):
        '''
        When bot has fully logged on
        Log bots username and ID
        Then load cogs
        '''

        if self.config.debug_channel_id is None:
            logger.warning("No debug channel set in config.")
        else:
            self.debug_chan = self.get_channel(int(self.config.debug_channel_id))

        # Setup mandatory cogs
        self.add_cog(Journal(self))
        logger.info("Loaded mandatory cog: Journal")

        self.add_cog(Reloader(self))
        logger.info("Loaded mandatory cog: Reloader")

        def _cog_ok(cog):
            # Special files
            if cog.startswith('_'):
                return False

            # Check for mandatory cogs
            if cog in Reloader.MANDATORY_COGS:
                return False

            # Cog is a directory
            return os.path.isdir(f'futaba/cogs/{cog}')

        files = [cog for cog in os.listdir('futaba/cogs') if _cog_ok(cog)]
        logger.info("Cogs found: %s", ', '.join(files))

        # Load cogs
        for file in files:
            try:
                self.load_extension(f'futaba.cogs.{file}')
            except Exception as error:
                # Something made the loading fail
                # So log it with reason and tell user to check it
                logger.error("Load failed: %s", file, exc_info=error)
                continue
            else:
                logger.info("Loaded cog: %s", file)

        # Register logger to catch journal events
        listener = LoggingOutputListener(self.journal_cog.router, '/')
        self.journal_cog.router.register(listener)

        # Performing migrations
        self.sql.guilds.migrate(self)

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
        '''
        A utility method for instantiating a bound Broadcaster on the given path.
        '''

        return Broadcaster(self.journal_cog.router, root)

    async def on_guild_join(self, guild):
        '''
        Event for handling joining a new guild.
        Adds it to the database for triggering guild migration in the database.
        '''

        logger.info("Guild join event for '%s' (%d)", guild.name, guild.id)
        with self.sql.transaction():
            self.sql.guilds.add_guild(guild)

    async def on_guild_remove(self, guild):
        '''
        Event for handling leaving a guild.
        Removes it to the database for triggering guild migration in the database.
        '''

        logger.info("Guild leave event for '%s' (%d)", guild.name, guild.id)
        with self.sql.transaction():
            self.sql.guilds.add_guild(guild)

    async def on_command_error(self, ctx, error):
        '''
        Handles errors when a command is invoked but raises an exception.
        '''

        # Complains about "context" vs "ctx".
        # pylint: disable=arguments-differ

        logger.error("Error during command!", exc_info=error)

        if isinstance(error, commands.errors.CommandNotFound):
            # Ignore no command found as we don't care if it wasn't one of our commands
            pass

        elif isinstance(error, commands.errors.CheckFailure):
            # Tell the user they don't have the permission to tun the command
            await Reactions.DENY.add(ctx.message)

        elif isinstance(error, CommandFailed):
            # The command failed, report the error message (if any) and send the FAIL reaction
            if error.kwargs:
                await ctx.send(**error.kwargs)

            await Reactions.FAIL.add(ctx.message)

        elif isinstance(error, InvalidCommandContext):
            # Explicitly ignore, this command was not even meant to be invoked in the first place
            # This is sent when we explicitly DO NOT want to add a SUCCESS reaction
            pass

        elif isinstance(error, SendHelp):
            # TODO send help message for error.command
            pass

    # Remove this?
    async def _send(self, *args, **kwargs):
        if self.debug_chan is not None:
            await self.debug_chan.send(*args, **kwargs)
