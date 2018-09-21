#
# sql/filter.py
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
Has the model for persisting filter settings.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import defaultdict, namedtuple

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Boolean, Column, Enum, LargeBinary, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from futaba.enums import FilterType, LocationType
from futaba.unicode import normalize_caseless

from ..hooks import register_hook

FilterSettings = namedtuple('FilterSettings', ('reupload',))
Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'FilterModel',
]

class FilterModel:
    __slots__ = (
        'sql',
        'tb_filters',
        'tb_content_filters',
        'tb_filter_immune_users',
        'tb_filter_settings',
        'filter_cache',
        'content_filter_cache',
        'immune_users_cache',
        'settings_cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_filters = Table('filters', meta,
                Column('location_id', BigInteger),
                Column('location_type', Enum(LocationType)),
                Column('filter_type', Enum(FilterType)),
                Column('text', Unicode),
                UniqueConstraint('location_id', 'location_type', 'text', name='filter_uq'))
        self.tb_content_filters = Table('content_filters', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id')),
                Column('filter_type', Enum(FilterType)),
                Column('hashsum', LargeBinary),
                UniqueConstraint('guild_id', 'hashsum', name='content_filter_uq'))
        self.tb_filter_immune_users = Table('filter_immune_users', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id')),
                Column('user_id', BigInteger),
                UniqueConstraint('guild_id', 'user_id', name='filter_immune_users_uq'))
        self.tb_filter_settings = Table('filter_reupload', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id'), primary_key=True),
                Column('reupload', Boolean))
        self.filter_cache = {}
        self.content_filter_cache = {}
        self.immune_users_cache = defaultdict(set)
        self.settings_cache = {}

        register_hook('on_guild_join', self.add_filter_settings)
        register_hook('on_guild_leave', self.remove_filter_settings)

    def get_filters(self, location):
        logger.debug("Getting filters for location '%s' (%d)", location.name, location.id)
        if location in self.filter_cache:
            logger.debug("Filter list was found in cache, returning")
            return self.filter_cache[location]

        sel = select([self.tb_filters.c.filter_type, self.tb_filters.c.text]) \
                .where(and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                ))
        result = self.sql.execute(sel)

        filters = {text: filter_type for (filter_type, text) in result.fetchall()}
        self.filter_cache[location] = filters
        return filters

    def add_filter(self, location, filter_type, text):
        logger.info("Adding text %r to filter, level '%s'", text, filter_type.value)

        text = normalize_caseless(text)
        ins = self.tb_filters \
                .insert() \
                .values(
                    location_id=location.id,
                    location_type=LocationType.of(location),
                    filter_type=filter_type,
                    text=text,
                )

        try:
            self.sql.execute(ins)
            self.filter_cache[location][text] = filter_type
        except IntegrityError as error:
            logger.error("Unable to insert new filter", exc_info=error)
            raise ValueError("This filter already exists")

    def update_filter(self, location, filter_type, text):
        logger.info("Updating filter %r to level '%s'", text, filter_type.value)

        text = normalize_caseless(text)
        upd = self.tb_filters \
                .update() \
                .values(filter_type=filter_type) \
                .where(and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                    self.tb_filters.c.filter_type == filter_type,
                    self.tb_filters.c.text == text,
                ))
        self.sql.execute(upd)
        self.filter_cache[location][text] = filter_type

    def delete_filter(self, location, text):
        logger.info("Deleting filter %r", text)

        delet = self.tb_filters \
                    .delete() \
                    .where(and_(
                        self.tb_filters.c.location_id == location.id,
                        self.tb_filters.c.location_type == LocationType.of(location),
                        self.tb_filters.c.text == text,
                    ))
        result = self.sql.execute(delet)
        self.filter_cache[location].pop(text, None)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
        return bool(result.rowcount)

    def get_content_filters(self, guild):
        logger.debug("Getting content filters for guild '%s' (%d)", guild.name, guild.id)
        if guild in self.content_filter_cache:
            logger.debug("Content filter list found in cache, returning")
            return self.content_filter_cache[guild]

        sel = select([self.tb_content_filters.c.filter_type, self.tb_content_filters.c.hashsum]) \
                .where(self.tb_content_filters.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        filters = {hashsum: filter_type for (filter_type, hashsum) in result.fetchall()}
        self.content_filter_cache[guild] = filters
        return filters

    def add_content_filter(self, guild, filter_type, hashsum):
        logger.info("Adding MD5 hash %s to filter, level '%s'", hashsum.hex(), filter_type.value)

        ins = self.tb_content_filters \
                .insert() \
                .values(
                    guild_id=guild.id,
                    filter_type=filter_type,
                    hashsum=hashsum,
                )

        try:
            self.sql.execute(ins)
            self.content_filter_cache[guild][hashsum] = filter_type
        except IntegrityError as error:
            logger.error("Unable to insert new content filter", exc_info=error)
            raise ValueError("This content filter already exists")

    def update_content_filter(self, guild, filter_type, hashsum):
        logger.info("Updating MD5 hash %s to filter, level '%s'", hashsum.hex(), filter_type.value)

        upd = self.tb_content_filters \
                .update() \
                .values(filter_type=filter_type) \
                .where(and_(
                    self.tb_content_filters.c.guild_id == guild.id,
                    self.tb_content_filters.c.filter_type == filter_type,
                    self.tb_content_filters.c.hashsum == hashsum,
                ))
        self.sql.execute(upd)
        self.content_filter_cache[guild][hashsum] = filter_type

    def delete_content_filter(self, guild, hashsum):
        logger.info("Deleting MD5 hash %s from filter", hashsum.hex())

        delet = self.tb_content_filters \
                    .delete() \
                    .where(and_(
                        self.tb_content_filters.c.guild_id == guild.id,
                        self.tb_content_filters.c.hashsum == hashsum,
                    ))
        result = self.sql.execute(delet)
        self.content_filter_cache[guild].pop(hashsum, None)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
        return bool(result.rowcount)

    def get_filter_immune_users(self, guild):
        logger.info("Getting users about filter immunity in guild '%s' (%d)", guild.name, guild.id)

        sel = select([self.tb_filter_immune_users.c.user_id]) \
                .where(self.tb_filter_immune_users.c.guild_id == guild.id)
        result = self.sql.execute(sel)
        self.immune_users_cache[guild].update(user_id for user_id, in result.fetchall())
        return self.immune_users_cache[guild]

    def user_is_filter_immune(self, guild, user):
        logger.debug("Checking if user '%s' (%d) is filter immune in guild '%s' (%d)",
                user.name, user.id, guild.name, guild.id)

        return user.id in self.immune_users_cache[guild]

    def add_filter_immune_user(self, guild, user):
        logger.info("Adding user '%s' (%d) to filter immune list for guild '%s' (%d)",
                user.name, user.id, guild.name, guild.id)

        ins = self.tb_filter_immune_users \
                .insert() \
                .values(
                    guild_id=guild.id,
                    user_id=user.id,
                )

        try:
            self.sql.execute(ins)
            self.immune_users_cache[guild].add(user.id)
            return True
        except IntegrityError:
            logger.debug("User is already on the list")
            return False

    def remove_filter_immune_user(self, guild, user):
        logger.info("Removing user '%s' (%d) to filter immune list for guild '%s' (%d)",
                user.name, user.id, guild.name, guild.id)

        delet = self.tb_filter_immune_users \
                    .delete() \
                    .where(and_(
                        self.tb_filter_immune_users.c.guild_id == guild.id,
                        self.tb_filter_immune_users.c.user_id == user.id,
                    ))
        result = self.sql.execute(delet)
        self.immune_users_cache[guild].remove(user.id)
        assert result.rowcount in (0, 1), "Only one matching user"
        return bool(result.rowcount)

    def get_filter_settings(self, guild):
        logger.info("Getting filter settings for guild '%s' (%d)", guild.name, guild.id)

        sel = select([self.tb_filter_settings.c.reupload]) \
                .where(self.tb_filter_settings.c.guild_id == guild.id)
        result = self.sql.execute(sel)
        reupload, = result.fetchone()
        self.settings_cache[guild] = FilterSettings(reupload=reupload)

    def add_filter_settings(self, guild):
        logger.info("Adding filter settings for guild '%s' (%d)", guild.name, guild.id)

        ins = self.tb_filter_settings \
                .insert() \
                .values(reupload=True)
        self.sql.execute(ins)
        self.settings_cache[guild] = FilterSettings(reupload=True)

    def update_filter_settings(self, guild, reupload):
        logger.info("Updating filter settings for guild '%s' (%d)", guild.name, guild.id)

        upd = self.tb_filter_settings \
                .update() \
                .values(reupload=reupload) \
                .where(self.tb_filter_settings.c.guild_id == guild.id)
        self.sql.execute(upd)
        self.settings_cache[guild] = FilterSettings(reupload=reupload)

    def remove_filter_settings(self, guild):
        logger.info("Removing filter settings for guild '%s' (%d)", guild.name, guild.id)

        delet = self.tb_filter_settings \
                    .delete() \
                    .where(self.tb_filter_settings.c.guild_id == guild.id)
        result = self.sql.execute(delet)
        self.settings_cache.pop(guild, None)
