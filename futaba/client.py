#
# client.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# mawabot is available free of charge under the terms of the MIT
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

logger = logging.getLogger(__name__)

class Bot(commands.AutoShardedBot):
    '''
    The custom discord ext bot
    '''

    __slots__ = (
        'config',
        'logger',
        'start_time',
        'debug_chan',
    )

    def __init__(self, config):
        self.config = config
        self.start_time = datetime.datetime.utcnow()
        self.debug_chan = None
        super().__init__(command_prefix=config['prefix'],
                         description='futaba - A discord mod bot',
                         pm_help=True)

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

        if not self.config['token']:
            logger.critical('Token is empty. Please open the config file and add the bot\'s token!')
        else:
            return self.run(self.config['token'])

    async def on_ready(self):
        '''
        When bot has fully logged on
        Log bots username and ID
        Then load cogs
        '''

        if self.config['debug-channel'] is None:
            logger.warning('No debug channel set in config.')
        else:
            self.debug_chan = self.get_channel(int(self.config['debug-channel']))

        self.add_cog(utils.Reloader(self))
        logger.info('Loaded cog: Reloader')

        def _cog_ok(cog):
            return cog[0] != '_' and os.path.isdir(f'futaba/cogs/{cog}')

        files = [cog for cog in os.listdir('futaba/cogs') if _cog_ok(cog)]
        logger.debug(f'Cogs found: {files}')

        for file in files:
            try:
                self.load_extension(f'futaba.cogs.{file}')
            except Exception as error:
                # Something made the loading fail
                # So log it with reason and tell user to check it
                logger.debug(f'Load failed: {file}', exc_info=error)
                continue
            else:
                logger.info(f'Loaded cog: {file}')

        channels = sum(1 for _ in self.get_all_channels())
        logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        logger.info('Connected to:')
        logger.info(f'* {len(self.guilds)} guilds')
        logger.info(f'* {channels} channels')
        logger.info(f'* {len(self.users)} users')
        logger.info('------')
        logger.info('Ready!')

    async def on_command_error(self, ctx, error):
        '''
        Deals with errors when a command is invoked.
        '''

        if isinstance(error, commands.errors.CommandNotFound):
            # Ignore no command found as we don't care if it wasn't one of our commands
            pass

        elif isinstance(error, commands.errors.CheckFailure):
            # Tell the user they don't have the permission to tun the command
            await utils.react(ctx.message, utils.Reactions.DENY)

    async def _send(self, *args, **kwargs):
        if self.debug_chan is None:
            logger.warning('No debug channel set!')
        else:
            await self.debug_chan.send(*args, **kwargs)
