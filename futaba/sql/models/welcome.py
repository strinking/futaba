#
# sql/models/welcome.py
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
Has the model for managing the welcome cog and its functionality.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

import discord
from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'WelcomeModel',
    'WelcomeStorage',
]

class WelcomeStorage:
    __slots__ = (
        'guild',
        'welcome_message',
        'welcome_channel',
    )

    def __init__(self, guild, welcome_message, welcome_channel_id):
        self.guild = guild
        self.welcome_message = welcome_message
        self.welcome_channel = discord.utils.get(guild.roles, id=welcome_channel_id)

    @property
    def message(self):
        return self.welcome_message

    @property
    def channel(self):
        return self.welcome_channel

class WelcomeModel:
    __slots__ = (
        'sql',
        'tb_welcome',
        'cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_welcome = Table('welcome', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id'), primary_key=True),
                Column('welcome_message', Unicode, nullable=True),
                Column('welcome_channel_id', BigInteger, nullable=True))
        self.cache = {}

        register_hook('on_guild_join', self.add_welcome)
        register_hook('on_guild_leave', self.del_welcome)

    def add_welcome(self, guild):
        logger.info("Adding welcome message row for guild '%s' (%d)", guild.name, guild.id)
        ins = self.tb_welcome \
                .insert() \
                .values(guild_id=guild.id, welcome_message=None, welcome_channel_id=None)
        self.sql.execute(ins)
        self.cache[guild] = WelcomeStorage(guild, None, None)

    def del_welcome(self, guild):
        logger.info("Removing welcome message row for guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_welcome \
                .delete() \
                .where(self.tb_welcome.c.guild_id == guild.id)
        self.sql.execute(delet)
        self.cache.pop(guild, None)

    def get_welcome(self, guild):
        logger.info("Getting welcome message data for guild '%s' (%d)", guild.name, guild.id)
        if guild in self.cache:
            logger.debug("Welcome message data found in cache, returning")
            return self.cache[guild]

        sel = select([self.tb_welcome.c.welcome_message, self.tb_welcome.c.welcome_channel_id]) \
                .where(self.tb_welcome.c.guild_id == guild.id)
        result = self.sql.execute(sel)
        welcome_message, welcome_channel_id = result.fetchone()

        welcome = WelcomeStorage(guild, welcome_message, welcome_channel_id)
        self.cache[guild] = welcome
        return welcome

    def set_welcome_message(self, guild, welcome_message):
        logger.info("Setting welcome message to %r for guild '%s' (%d)",
                welcome_message, guild.name, guild.id)

        upd = self.tb_welcome \
                .update() \
                .where(self.tb_welcome.c.guild_id == guild.id) \
                .values(welcome_message=welcome_message)
        self.sql.execute(upd)
        self.cache[guild].welcome_message = welcome_message

    def set_welcome_channel(self, guild, channel):
        if channel is None:
            logger.info("Unsetting welcome channel for guild '%s' (%d)",
                    guild.name, guild.id)
        else:
            logger.info("Setting welcome channel to #%s (%d) for guild '%s' (%d)",
                    channel.name, channel.id, guild.name, guild.id)

        upd = self.tb_welcome \
                .update() \
                .where(self.tb_welcome.c.guild_id == guild.id) \
                .values(welcome_channel_id=getattr(channel, 'id', None))
        self.sql.execute(upd)
        self.cache[guild].welcome_channel = channel
