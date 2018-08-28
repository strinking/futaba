#
# client.py
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
Holds the custom discord client
'''

import logging
import datetime
import os

import discord
from discord.ext import commands

from . import utils
from .config import Configuration
from .sql import SqlHandler
from .utils import plural

logger = logging.getLogger(__name__)

class Bot(commands.AutoShardedBot):
    __slots__ = (
        'config',
        'logger',
        'start_time',
        'debug_chan',
        'sql',
    )

    def __init__(self, config: Configuration):
        self.config = config
        self.start_time = datetime.datetime.utcnow()
        self.debug_chan = None
        self.sql = SqlHandler(config.database_url)
        super().__init__(command_prefix=self.get_prefix_sql,
                         description='futaba - A discord mod bot',
                         pm_help=True)

    def get_prefix_sql(self, message):
        prefix = None

        if message.guild is not None:
            prefix = self.sql.settings.get_prefix(message.guild)

        prefix = prefix or self.config.default_prefix
        return commands.when_mentioned_or(prefix)(self, message)

    @property
    def uptime(self):
        '''
        Gets the uptime for the bot
        '''
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

        self.add_cog(utils.Reloader(self))
        logger.info("Loaded cog: Reloader")

        def _cog_ok(cog):
            return not cog.startswith('_') and os.path.isdir(f'futaba/cogs/{cog}')

        files = [cog for cog in os.listdir('futaba/cogs') if _cog_ok(cog)]
        logger.info("Cogs found: %s", ', '.join(files))

        for file in files:
            try:
                self.load_extension(f'futaba.cogs.{file}')
            except Exception as error:
                # Something made the loading fail
                # So log it with reason and tell user to check it
                logger.debug("Load failed: %s", file, exc_info=error)
                continue
            else:
                logger.info("Loaded cog: %s", file)

        logger.info("Logged in as %s (%d)", self.user.name, self.user.id)
        logger.info("Connected to:")
        logger.info("* %d guild%s", len(self.guilds), plural(len(self.guilds)))
        logger.info("* %d channels", sum(1 for _ in self.get_all_channels()))
        logger.info("* %d users", len(self.users))
        logger.info("------")
        logger.info("Ready!")

    async def on_command_error(self, ctx, error):
        '''
        Deals with errors when a command is invoked.
        '''

        # Complains about "context" vs "ctx".
        # pylint: disable=arguments-differ

        if isinstance(error, commands.errors.CommandNotFound):
            # Ignore no command found as we don't care if it wasn't one of our commands
            pass

        elif isinstance(error, commands.errors.CheckFailure):
            # Tell the user they don't have the permission to tun the command
            await utils.react(ctx.message, utils.Reactions.DENY)

    async def _send(self, *args, **kwargs):
        if self.debug_chan is not None:
            await self.debug_chan.send(*args, **kwargs)
