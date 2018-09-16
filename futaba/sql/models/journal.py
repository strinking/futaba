#
# sql/models/journal.py
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
Stores configured information about where journal information should
be logged into Discord text channels within guilds.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import defaultdict, namedtuple

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Boolean, Column, Table, Text
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
ConfiguredChannelOutput = namedtuple('ConfiguredChannelOutput', ('channel', 'path', 'settings'))
logger = logging.getLogger(__name__)

__all__ = [
    'ConfiguredChannelOutput',
    'ChannelSettings',
    'JournalModel',
]

class ChannelSettings:
    __slots__ = (
        'recursive',
    )

    def __init__(self, recursive):
        self.recursive = recursive

class JournalModel:
    __slots__ = (
        'sql',
        'tb_journal_outputs',
        'journal_outputs_cache',
        'journal_guild_cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_journal_outputs = Table('journal_outputs', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id')),
                Column('channel_id', BigInteger, primary_key=True),
                Column('path', Text, primary_key=True),
                Column('recursive', Boolean),
                UniqueConstraint('guild_id', 'channel_id', 'path', name='journal_outputs_uq'))
        self.journal_outputs_cache = defaultdict(dict)
        self.journal_guild_cache = set()

        register_hook('on_guild_leave', self.delete_journal_channels)

    def add_journal_channel(self, channel, path, recursive):
        logger.info("Adding journal channel for #%s (%d) on path %s",
                channel.name, channel.id, path)
        logger.debug("Settings: recursive = %r", recursive)

        assert channel.guild is not None, "Channel must a guild channel"
        ins = self.tb_journal_outputs \
                    .insert() \
                    .values(
                        guild_id=channel.guild.id,
                        channel_id=channel.id,
                        path=path,
                        recursive=recursive,
                    )

        try:
            self.sql.execute(ins)
            self.journal_outputs_cache[channel][path] = ChannelSettings(recursive=recursive)
        except IntegrityError as error:
            logger.error("Unable to insert new journal channel", exc_info=error)
            raise ValueError("This channel already tracks the given path")

    def update_journal_channel(self, channel, path, recursive):
        logger.info("Updating journal channel for #%s (%d) on path %s",
                channel.name, channel.id, path)
        logger.debug("Settings: recursive = %r", recursive)

        assert channel.guild is not None, "Channel must a guild channel"
        upd = self.tb_journal_outputs \
                    .update() \
                    .values(recursive=recursive) \
                    .where(and_(
                        self.tb_journal_outputs.c.guild_id == channel.guild.id,
                        self.tb_journal_outputs.c.channel_id == channel.id,
                        self.tb_journal_outputs.c.path == path,
                    ))

        self.sql.execute(upd)
        settings = self.journal_outputs_cache[channel][path]
        settings.recursive = recursive

    def delete_journal_channel(self, channel, path):
        logger.info("Deleting journal channel for #%s (%d) on path '%s'",
                channel.name, channel.id, path)

        assert channel.guild is not None, "Channel must be a guild channel"
        delet = self.tb_journal_outputs \
                    .delete() \
                    .where(and_(
                        self.tb_journal_outputs.c.guild_id == channel.guild.id,
                        self.tb_journal_outputs.c.channel_id == channel.id,
                        self.tb_journal_outputs.c.path == path,
                    ))

        result = self.sql.execute(delet)
        self.journal_outputs_cache[channel].pop(path, None)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
        return bool(result.rowcount)

    def has_journal_channel(self, channel, path):
        logger.info("Checking for journal channel on #%s (%d) for path '%s'",
                channel.name, channel.id, path)
        return path in self.journal_outputs_cache[channel]

    def get_journal_channels(self, guild):
        logger.info("Fetching all journal channel outputs for guild '%s' (%d)",
                guild.name, guild.id)

        if guild not in self.journal_guild_cache:
            logger.debug("Guild not in cache list, fetching from database")

            # Perform SELECT
            logger.debug("Guild not loaded from disk, doing select")
            sel = select([
                        self.tb_journal_outputs.c.channel_id,
                        self.tb_journal_outputs.c.path,
                        self.tb_journal_outputs.c.recursive,
                    ]) \
                    .where(self.tb_journal_outputs.c.guild_id == guild.id)
            result = self.sql.execute(sel)

            # Update cache
            for channel_id, path, recursive in result.fetchall():
                channel = guild.get_channel(channel_id)
                self.journal_outputs_cache[channel][path] = ChannelSettings(recursive=recursive)

        # Compile guild list
        outputs = []
        for channel in guild.channels:
            for path, settings in self.journal_outputs_cache[channel].items():
                outputs.append(ConfiguredChannelOutput(channel=channel, path=path, settings=settings))
        return outputs

    def delete_journal_channels(self, guild):
        logger.info("Removing all journal channel outputs for guild '%s' (%d)",
                guild.name, guild.id)
        delet = self.tb_journal_outputs \
                    .delete() \
                    .where(self.tb_journal_outputs.c.guild_id == guild.id)
        result = self.sql.execute(delet)
