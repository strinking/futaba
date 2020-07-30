#
# sql/models/journal.py
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
Stores configured information about where journal information should
be logged into Discord text channels within guilds.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import defaultdict

from sqlalchemy import and_
from sqlalchemy import BigInteger, Boolean, Column, Enum, Table, Text
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from futaba.enums import LocationType
from ..data import ConfiguredJournalOutput, JournalOutputData

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["JournalModel"]


class JournalModel:
    __slots__ = (
        "sql",
        "tb_journal_outputs",
        "journal_outputs_cache",
        "journal_guild_cache",
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_journal_outputs = Table(
            "journal_outputs",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("location_id", BigInteger, primary_key=True),
            Column("location_type", Enum(LocationType)),
            Column("path", Text, primary_key=True),
            Column("recursive", Boolean),
            CheckConstraint(
                "location_type != 'GUILD'", name="journal_outputs_sendable_check"
            ),
            UniqueConstraint(
                "guild_id",
                "location_id",
                "location_type",
                "path",
                name="journal_outputs_uq",
            ),
        )
        self.journal_outputs_cache = defaultdict(dict)
        self.journal_guild_cache = set()

    def add_journal_output(self, guild, location, path, recursive):
        location_type = LocationType.of(location)
        if location_type == LocationType.CHANNEL:
            logger.info(
                "Adding journal output for channel #%s (%d) on path %s",
                location.name,
                location.id,
                path,
            )
        elif location_type == LocationType.USER:
            logger.info(
                "Adding journal output for user '%s' (%d) on path %s",
                location.name,
                location.id,
                path,
            )
        else:
            raise TypeError(f"Invalid type for location: {location!r}")

        logger.debug("Settings: recursive = %r", recursive)

        ins = self.tb_journal_outputs.insert().values(
            guild_id=guild.id,
            location_id=location.id,
            location_type=location_type,
            path=path,
            recursive=recursive,
        )

        try:
            self.sql.execute(ins)
            self.journal_outputs_cache[location][path] = JournalOutputData(
                recursive=recursive
            )
        except IntegrityError as error:
            logger.error("Unable to insert new journal location", exc_info=error)
            raise ValueError("This output already tracks the given path")

    def update_journal_output(self, guild, location, path, recursive):
        location_type = LocationType.of(location)
        if location_type == LocationType.CHANNEL:
            logger.info(
                "Updating journal output for channel #%s (%d) on path %s",
                location.name,
                location.id,
                path,
            )
        elif location_type == LocationType.USER:
            logger.info(
                "Updating journal output for user '%s' (%d) on path %s",
                location.name,
                location.id,
                path,
            )
        else:
            raise TypeError(f"Invalid type for location: {location!r}")

        logger.debug("Settings: recursive = %r", recursive)

        upd = (
            self.tb_journal_outputs.update()
            .values(recursive=recursive)
            .where(
                and_(
                    self.tb_journal_outputs.c.guild_id == guild.id,
                    self.tb_journal_outputs.c.location_id == location.id,
                    self.tb_journal_outputs.c.location_type == location_type,
                    self.tb_journal_outputs.c.path == path,
                )
            )
        )

        self.sql.execute(upd)
        settings = self.journal_outputs_cache[location][path]
        settings.recursive = recursive

    def delete_journal_output(self, guild, location, path):
        location_type = LocationType.of(location)
        if location_type == LocationType.CHANNEL:
            logger.info(
                "Deleting journal output for channel #%s (%d) on path '%s'",
                location.name,
                location.id,
                path,
            )
        elif location_type == LocationType.USER:
            logger.info(
                "Deleting journal output for user '%s' (%d) on path '%s'",
                location.name,
                location.id,
                path,
            )
        else:
            raise TypeError(f"Invalid type for location: {location!r}")

        delet = self.tb_journal_outputs.delete().where(
            and_(
                self.tb_journal_outputs.c.guild_id == guild.id,
                self.tb_journal_outputs.c.location_id == location.id,
                self.tb_journal_outputs.c.location_type == location_type,
                self.tb_journal_outputs.c.path == path,
            )
        )

        result = self.sql.execute(delet)
        self.journal_outputs_cache[location].pop(path, None)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
        return bool(result.rowcount)

    def has_journal_channel(self, channel, path):
        logger.info(
            "Checking for journal output on channel #%s (%d) for path '%s'",
            channel.name,
            channel.id,
            path,
        )
        return path in self.journal_outputs_cache[channel]

    def has_journal_user(self, user, path):
        logger.info(
            "Checking for journal output on user '%s' (%d) for path '%s'",
            user.name,
            user.id,
            path,
        )
        return path in self.journal_outputs_cache[user]

    def fetch_journal_channels(self, guild):
        logger.info(
            "Fetching all journal channel outputs for guild '%s' (%d)",
            guild.name,
            guild.id,
        )

        sel = select(
            [
                self.tb_journal_outputs.c.location_id,
                self.tb_journal_outputs.c.path,
                self.tb_journal_outputs.c.recursive,
            ]
        ).where(
            and_(
                self.tb_journal_outputs.c.guild_id == guild.id,
                self.tb_journal_outputs.c.location_type == LocationType.CHANNEL,
            )
        )
        result = self.sql.execute(sel)

        # Update cache
        for channel_id, path, recursive in result.fetchall():
            channel = guild.get_channel(channel_id)
            self.journal_outputs_cache[channel][path] = JournalOutputData(
                recursive=recursive
            )

        # Compile guild list
        return self.get_journals_on_channels(*guild.channels)

    def fetch_journal_users(self, bot, guild):
        logger.info(
            "Fetching all journal user outputs in guild '%s' (%d)", guild.name, guild.id
        )

        sel = select(
            [
                self.tb_journal_outputs.c.location_id,
                self.tb_journal_outputs.c.path,
                self.tb_journal_outputs.c.recursive,
            ]
        ).where(
            and_(
                self.tb_journal_outputs.c.guild_id == guild.id,
                self.tb_journal_outputs.c.location_type == LocationType.USER,
            )
        )
        result = self.sql.execute(sel)

        # Update cache
        users = []
        for user_id, path, recursive in result.fetchall():
            user = bot.get_user(user_id)
            self.journal_outputs_cache[user][path] = JournalOutputData(
                recursive=recursive
            )
            users.extend(self.get_journals_on_user(user))

        # Compile user list
        return users

    def get_journals_on_channels(self, *channels):
        logger.debug(
            "Getting all journal paths from cache on channels: [%s]",
            ", ".join(f"#{channel.name} ({channel.id})" for channel in channels),
        )

        for channel in channels:
            for path, settings in self.journal_outputs_cache[channel].items():
                yield ConfiguredJournalOutput(
                    sink=channel, path=path, settings=settings
                )

    def get_journals_on_user(self, user):
        logger.debug(
            "Getting all journal paths from cache on user: '%s' (%d)",
            user.name,
            user.id,
        )

        for path, settings in self.journal_outputs_cache[user].items():
            yield ConfiguredJournalOutput(sink=user, path=path, settings=settings)
