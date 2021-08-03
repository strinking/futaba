#
# client.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2021 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Contains the discord client for the bot
"""

import logging
import sys
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from .config import Config
from .utils import plural

logger = logging.getLogger(__name__)


class Bot(commands.AutoShardedBot):
    __slots__ = (
        "config",
        "start_time",
    )

    def __init__(self, config: Config):
        self.config = config
        self.start_time = datetime.utcnow()
        self.error_channel = None

        super().__init__(
            command_prefix=commands.when_mentioned_or(self.config.prefix),
            description="futaba - A Discord Mod bot for the Programming server",
            chunk_guilds_at_startup=True,
            intents=discord.Intents.all(),
        )

    @property
    def uptime(self) -> timedelta:
        """Gets bot's uptime"""

        return datetime.utcnow() - self.start_time

    def run_with_token(self):
        """Runs the bot using the run command using the token given in the config"""

        if not self.config.token:
            logger.critical("Token is missing! Please check the config file")
            sys.exit(1)
        else:
            self.run(self.config.token)

    async def on_ready(self):
        """Runs after bot has logged in and is ready. Loads music cogs and other commands"""

        # Get error channel
        if self.config.error_channel_id:
            channel = self.get_channel(self.config.error_channel_id)
            if isinstance(channel, discord.TextChannel):
                self.error_channel = channel

        # Finished
        pyver = sys.version_info
        logger.info(f"Powered by Python {pyver.major}.{pyver.minor}.{pyver.micro}")
        logger.info(f"Using discord.py {discord.__version__}")
        logger.info(f"Logged in as {self.user.name} ({self.user.id})")
        logger.info("Connected to:")
        logger.info(f"* {len(self.guilds)} guild{plural(len(self.guilds))}")
        logger.info(f"* {sum(1 for _ in self.get_all_channels())} channels")
        logger.info(f"* {len(self.users)} users")
        logger.info("------")
        logger.info("Ready!")
