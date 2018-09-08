#
# sql/models/settings.py
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
Has the model for managing persistent bot settings.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Boolean, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from ..hooks import on_guild_join, on_guild_leave

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'SettingsModel',
]

# TODO make this file a directory and move this to its own file?
class FilterSettingsStorage:
    __slots__ = (
        'bot_immune',
        'manage_messages_immune',
    )

    def __init__(self):
        self.bot_immune = False
        self.manage_messages_immune = True

    def updated(self, field, value=None):
        '''
        Sets 'field' if 'value' is not None. Returns the current value of 'field'.
        Useful for getting an excluded field, and updating the storage object too.
        '''

        if value is None:
            setattr(self, field, value)

        return getattr(self, field)

class SettingsModel:
    __slots__ = (
        'sql',
        'tb_prefixes',
        'tb_filter_settings',
        'prefix_cache',
        'filter_settings_cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_prefixes = Table('prefixes', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id'), primary_key=True),
                Column('prefix', Unicode, nullable=True))
        self.tb_filter_settings = Table('filter_settings', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id'), primary_key=True),
                Column('bot_immune', Boolean),
                Column('manage_messages_immune', Boolean))
        self.prefix_cache = {}
        self.filter_settings_cache = {}

    @on_guild_join
    def add_prefix(self, guild):
        logger.info("Adding prefix row for new guild '%s' (%d)", guild.name, guild.id)
        ins = self.tb_prefixes \
                .insert() \
                .values(
                    guild_id=guild.id,
                    prefix=None,
                )
        self.sql.execute(ins)
        self.prefix_cache[guild] = None

    @on_guild_leave
    def del_prefix(self, guild):
        logger.info("Removing prefix row for departing guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_prefixes \
                    .delete() \
                    .where(self.tb_prefixes.c.guild_id == guild.id)
        self.sql.execute(delet)
        del self.prefix_cache[guild]

    def get_prefix(self, guild):
        logger.debug("Getting prefix for guild '%s' (%d)", guild.name, guild.id)
        if guild in self.prefix_cache:
            logger.debug("Prefix was found in cache, returning")
            return self.prefix_cache[guild]

        sel = select([self.tb_prefixes.c.prefix]) \
                .where(self.tb_prefixes.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_prefix(guild)
            return None

        prefix, = result.fetchone()
        self.prefix_cache[guild] = prefix
        return prefix

    def set_prefix(self, guild, prefix):
        logger.info("Setting prefix to '%s' for guild '%s' (%d)", prefix, guild.name, guild.id)
        upd = self.tb_prefixes \
                .update() \
                .where(self.tb_prefixes.c.guild_id == guild.id) \
                .values(prefix=prefix)
        self.sql.execute(upd)
        self.prefix_cache[guild] = prefix

    @on_guild_join
    def add_filter_settings(self, guild):
        logger.info("Adding row for bot filter immunity for new guild '%s' (%d)", guild.name, guild.id)
        storage = FilterSettingsStorage()
        ins = self.tb_filter_settings \
                .insert() \
                .values(
                    guild_id=guild.id,
                    bot_immune=storage.bot_immune,
                    manage_messages_immune=storage.manage_messages_immune,
                )
        self.sql.execute(ins)
        self.filter_settings_cache[guild] = storage

    @on_guild_leave
    def del_filter_settings(self, guild):
        logger.info("Removing row for bot filter immunity for departing guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_filter_settings \
                    .delete() \
                    .where(self.tb_filter_settings.c.guild_id == guild.id)
        self.sql.execute(delet)
        del self.filter_settings_cache[guild]

    def get_filter_settings(self, guild):
        logger.debug("Getting filter settings for guild '%s' (%d)", guild.name, guild.id)
        if guild in self.filter_settings_cache:
            logger.debug("Settings were found in cache, returning")
            return self.filter_settings_cache[guild]

        sel = select([self.tb_filter_settings.c.bot_immune, self.tb_filter_settings.c.manage_messages_immune]) \
                .where(self.tb_filter_settings.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_filter_settings(guild)
            return self.filter_settings_cache[guild]

        bot_immune, manage_messages_immune = result.fetchone()

        # Update cache
        storage = FilterSettingsStorage()
        storage.bot_immune = bot_immune
        storage.manage_messages_immune = manage_messages_immune
        self.filter_settings_cache[guild] = storage
        return storage

    def set_bot_filter_immunity(self, guild, bot_immune=None, manage_messages_immune=None):
        storage = self.filter_settings_cache[guild]
        bot_immune = storage.updated('bot_immune', bot_immune)
        manage_messages_immune = storage.updated('manage_messages_immune', manage_messages_immune)

        logger.info("Setting filter settings (bot_immune='%s', manage_messages_immune='%s') for guild '%s' (%d)",
                bot_immune, manage_messages_immune, guild.name, guild.id)
        upd = self.tb_filter_settings \
                .update() \
                .where(self.tb_filter_settings.c.guild_id == guild.id) \
                .values(
                    bot_immune=bot_immune,
                    manage_messages_immune=manage_messages_immune,
                )
        self.sql.execute(upd)
