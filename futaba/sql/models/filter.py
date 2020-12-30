#
# sql/filter.py
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
Has the model for persisting filter settings.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import defaultdict

from sqlalchemy import and_
from sqlalchemy import BigInteger, Boolean, Column, Enum, LargeBinary, Table, Unicode
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from futaba.enums import FilterType, LocationType
from futaba.unicode import normalize_caseless

from ..data import FilterSettingsData
from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)


__all__ = ["FilterModel"]


class FilterModel:
    __slots__ = (
        "sql",
        "tb_filters",
        "tb_content_filters",
        "tb_filter_immune_users",
        "tb_filter_settings",
        "filter_cache",
        "content_filter_cache",
        "immune_users_cache",
        "settings_cache",
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_filters = Table(
            "filters",
            meta,
            Column("location_id", BigInteger),
            Column("location_type", Enum(LocationType)),
            Column("filter_type", Enum(FilterType)),
            Column("text", Unicode),
            CheckConstraint(
                "location_type != 'USER'", name="filter_location_in_guild_check"
            ),
            UniqueConstraint("location_id", "location_type", "text", name="filter_uq"),
        )
        self.tb_content_filters = Table(
            "content_filters",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("filter_type", Enum(FilterType)),
            Column("hashsum", LargeBinary),
            Column("description", Unicode),
            UniqueConstraint("guild_id", "hashsum", name="content_filter_uq"),
        )
        self.tb_filter_immune_users = Table(
            "filter_immune_users",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("user_id", BigInteger),
            UniqueConstraint("guild_id", "user_id", name="filter_immune_users_uq"),
        )
        self.tb_filter_settings = Table(
            "filter_reupload",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("bot_immune", Boolean),
            Column("manage_messages_immune", Boolean),
            Column("reupload", Boolean),
        )
        self.filter_cache = {}
        self.content_filter_cache = {}
        self.immune_users_cache = defaultdict(set)
        self.settings_cache = {}

        register_hook("on_guild_join", self.add_settings)

    def get_filters(self, location):
        logger.debug(
            "Getting filters for location '%s' (%d)", location.name, location.id
        )
        if location in self.filter_cache:
            return self.filter_cache[location]

        sel = select([self.tb_filters.c.filter_type, self.tb_filters.c.text]).where(
            and_(
                self.tb_filters.c.location_id == location.id,
                self.tb_filters.c.location_type == LocationType.of(location),
            )
        )
        result = self.sql.execute(sel)

        filters = {text: filter_type for (filter_type, text) in result.fetchall()}
        self.filter_cache[location] = filters
        return filters

    def add_filter(self, location, filter_type, text):
        logger.info("Adding text %r to filter, level '%s'", text, filter_type.value)

        text = normalize_caseless(text)
        ins = self.tb_filters.insert().values(
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
        upd = (
            self.tb_filters.update()
            .values(filter_type=filter_type)
            .where(
                and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                    self.tb_filters.c.filter_type == filter_type,
                    self.tb_filters.c.text == text,
                )
            )
        )
        self.sql.execute(upd)
        self.filter_cache[location][text] = filter_type

    def delete_filter(self, location, text):
        logger.info("Deleting filter %r", text)

        delet = self.tb_filters.delete().where(
            and_(
                self.tb_filters.c.location_id == location.id,
                self.tb_filters.c.location_type == LocationType.of(location),
                self.tb_filters.c.text == text,
            )
        )
        result = self.sql.execute(delet)
        self.filter_cache[location].pop(text, None)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
        return bool(result.rowcount)

    def get_content_filters(self, guild):
        logger.debug(
            "Getting content filters for guild '%s' (%d)", guild.name, guild.id
        )
        if guild in self.content_filter_cache:
            return self.content_filter_cache[guild]

        sel = select(
            [
                self.tb_content_filters.c.filter_type,
                self.tb_content_filters.c.hashsum,
                self.tb_content_filters.c.description,
            ]
        ).where(self.tb_content_filters.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        filters = {
            hashsum: (filter_type, description)
            for (filter_type, hashsum, description) in result.fetchall()
        }
        self.content_filter_cache[guild] = filters
        return filters

    def add_content_filter(self, guild, filter_type, hashsum, description):
        logger.info(
            "Adding SHA1 hash %s to filter, level '%s'",
            hashsum.hex(),
            filter_type.value,
        )

        ins = self.tb_content_filters.insert().values(
            guild_id=guild.id,
            filter_type=filter_type,
            hashsum=hashsum,
            description=description,
        )

        try:
            self.sql.execute(ins)
            self.content_filter_cache[guild][hashsum] = (filter_type, description)
        except IntegrityError as error:
            logger.error("Unable to insert new content filter", exc_info=error)
            raise ValueError("This content filter already exists")

    def update_content_filter(self, guild, filter_type, hashsum, description):
        logger.info(
            "Updating SHA1 hash %s to filter, level '%s'",
            hashsum.hex(),
            filter_type.value,
        )

        upd = (
            self.tb_content_filters.update()
            .values(filter_type=filter_type, description=description)
            .where(
                and_(
                    self.tb_content_filters.c.guild_id == guild.id,
                    self.tb_content_filters.c.hashsum == hashsum,
                )
            )
        )
        self.sql.execute(upd)
        self.content_filter_cache[guild][hashsum] = (filter_type, description)

    def delete_content_filter(self, guild, hashsum):
        logger.info("Deleting SHA1 hash %s from filter", hashsum.hex())

        delet = self.tb_content_filters.delete().where(
            and_(
                self.tb_content_filters.c.guild_id == guild.id,
                self.tb_content_filters.c.hashsum == hashsum,
            )
        )
        result = self.sql.execute(delet)
        self.content_filter_cache[guild].pop(hashsum, None)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
        return bool(result.rowcount)

    def fetch_filter_immune_users(self, guild):
        logger.info(
            "Fetching users with filter immunity in guild '%s' (%d)",
            guild.name,
            guild.id,
        )

        sel = select([self.tb_filter_immune_users.c.user_id]).where(
            self.tb_filter_immune_users.c.guild_id == guild.id
        )
        result = self.sql.execute(sel)
        self.immune_users_cache[guild].update(user_id for user_id, in result.fetchall())
        return self.immune_users_cache[guild]

    def get_filter_immune_users(self, guild):
        logger.info(
            "Getting users with filter immunity in guild '%s' (%d)",
            guild.name,
            guild.id,
        )

        if guild not in self.immune_users_cache:
            self.fetch_filter_immune_users(guild)

        return self.immune_users_cache[guild]

    def user_is_filter_immune(self, guild, user):
        logger.debug(
            "Checking if user '%s' (%d) is filter immune in guild '%s' (%d)",
            user.name,
            user.id,
            guild.name,
            guild.id,
        )

        return user.id in self.get_filter_immune_users(guild)

    def add_filter_immune_user(self, guild, user):
        logger.info(
            "Adding user '%s' (%d) to filter immune list for guild '%s' (%d)",
            user.name,
            user.id,
            guild.name,
            guild.id,
        )

        ins = self.tb_filter_immune_users.insert().values(
            guild_id=guild.id, user_id=user.id
        )

        try:
            self.sql.execute(ins)
            self.immune_users_cache[guild].add(user.id)
            return True
        except IntegrityError:
            logger.debug("User is already on the list")
            return False

    def remove_filter_immune_user(self, guild, user):
        logger.info(
            "Removing user '%s' (%d) to filter immune list for guild '%s' (%d)",
            user.name,
            user.id,
            guild.name,
            guild.id,
        )

        delet = self.tb_filter_immune_users.delete().where(
            and_(
                self.tb_filter_immune_users.c.guild_id == guild.id,
                self.tb_filter_immune_users.c.user_id == user.id,
            )
        )
        result = self.sql.execute(delet)
        self.immune_users_cache[guild].remove(user.id)
        assert result.rowcount in (0, 1), "Only one matching user"
        return bool(result.rowcount)

    def fetch_settings(self, guild):
        logger.info("Getting filter settings for guild '%s' (%d)", guild.name, guild.id)

        sel = select(
            [
                self.tb_filter_settings.c.bot_immune,
                self.tb_filter_settings.c.manage_messages_immune,
                self.tb_filter_settings.c.reupload,
            ]
        ).where(self.tb_filter_settings.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_settings(guild)
            return self.settings_cache[guild.id]

        bot_immune, manage_messages_immune, reupload = result.fetchone()

        # Update cache
        storage = FilterSettingsData()
        storage.bot_immune = bot_immune
        storage.manage_messages_immune = manage_messages_immune
        storage.reupload = reupload
        self.settings_cache[guild.id] = storage
        return storage

    def get_settings(self, guild):
        logger.info(
            "Getting cached filter settings for guild '%s' (%d)", guild.name, guild.id
        )
        return self.settings_cache[guild.id]

    def add_settings(self, guild):
        logger.info("Adding filter settings for guild '%s' (%d)", guild.name, guild.id)
        storage = FilterSettingsData()
        ins = self.tb_filter_settings.insert().values(
            guild_id=guild.id,
            bot_immune=storage.bot_immune,
            manage_messages_immune=storage.manage_messages_immune,
            reupload=storage.reupload,
        )
        self.sql.execute(ins)
        self.settings_cache[guild.id] = storage

    def set_reupload(self, guild, reupload):
        logger.info(
            "Updating filter settings for guild '%s' (%d)", guild.name, guild.id
        )

        upd = (
            self.tb_filter_settings.update()
            .where(self.tb_filter_settings.c.guild_id == guild.id)
            .values(reupload=reupload)
        )
        self.sql.execute(upd)
        self.settings_cache[guild.id].reupload = reupload

    def set_bot_filter_immunity(
        self, guild, bot_immune=None, manage_messages_immune=None
    ):
        storage = self.settings_cache[guild.id]
        bot_immune = storage.updated("bot_immune", bot_immune)
        manage_messages_immune = storage.updated(
            "manage_messages_immune", manage_messages_immune
        )

        logger.info(
            "Updating filter settings (bot_immune='%s', manage_messages_immune='%s') for guild '%s' (%d)",
            bot_immune,
            manage_messages_immune,
            guild.name,
            guild.id,
        )
        upd = (
            self.tb_filter_settings.update()
            .where(self.tb_filter_settings.c.guild_id == guild.id)
            .values(
                bot_immune=bot_immune, manage_messages_immune=manage_messages_immune
            )
        )
        self.sql.execute(upd)
