#
# sql/models/settings.py
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
Has the model for managing persistent bot settings.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

from sqlalchemy import BigInteger, Boolean, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'SettingsModel',
]

class SettingsModel:
    __slots__ = (
        'sql',
        'tb_prefixes',
        'prefix_cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_prefixes = Table('prefixes', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id'), primary_key=True),
                Column('prefix', Unicode, nullable=True))
        self.prefix_cache = {}

        register_hook('on_guild_join', self.add_prefix)
        register_hook('on_guild_leave', self.del_prefix)

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

    def del_prefix(self, guild):
        logger.info("Removing prefix row for departing guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_prefixes \
                    .delete() \
                    .where(self.tb_prefixes.c.guild_id == guild.id)
        self.sql.execute(delet)
        self.prefix_cache.pop(guild, None)

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
