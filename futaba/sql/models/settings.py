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

"""
Has the model for managing persistent bot settings.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import enum
import functools
import logging

import discord

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    SmallInteger,
    Table,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.sql import select

from futaba.enums import LocationType
from futaba.utils import partition_on
from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["SettingsModel"]


class GuildSettingsStorage:
    __slots__ = ("prefix", "max_delete_messages", "warn_manual_mod_action")

    def __init__(self, prefix, max_delete_messages, warn_manual_mod_action):
        self.prefix = prefix
        self.max_delete_messages = max_delete_messages
        self.warn_manual_mod_action = warn_manual_mod_action


class SpecialRoleStorage:
    __slots__ = ("guild", "member_role", "guest_role", "mute_role", "jail_role")

    def __init__(
        self, guild, member_role_id, guest_role_id, mute_role_id, jail_role_id
    ):
        self.guild = guild
        self.member_role = self._get_role(member_role_id)
        self.guest_role = self._get_role(guest_role_id)
        self.mute_role = self._get_role(mute_role_id)
        self.jail_role = self._get_role(jail_role_id)

    def update(self, attrs):
        logger.debug("Updating special role storage: %s", attrs)
        if "member" in attrs:
            self.member_role = attrs["member"]
        if "guest" in attrs:
            self.guest_role = attrs["guest"]
        if "mute" in attrs:
            self.mute_role = attrs["mute"]
        if "jail" in attrs:
            self.jail_role = attrs["jail"]

    @property
    def member(self):
        return self.member_role

    @property
    def guest(self):
        return self.guest_role

    @property
    def mute(self):
        return self.mute_role

    @property
    def jail(self):
        return self.jail_role

    def _get_role(self, id):
        if id is None:
            return None

        return discord.utils.get(self.guild.roles, id=id)

    def __iter__(self):
        yield self.member_role
        yield self.guest_role
        yield self.mute_role
        yield self.jail_role


class TrackingBlacklistStorage:
    __slots__ = ("guild", "blacklisted_channels", "blacklisted_users")

    def __init__(self, guild, blacklist):
        # blacklist is an iterable of (type, data_id)

        self.guild = guild
        blacklisted_channels, blacklisted_users = partition_on(
            lambda block: block[0] is LocationType.CHANNEL,
            blacklist,
            lambda block: block[1],
        )

        self.blacklisted_channels, self.blacklisted_users = (
            set(blacklisted_channels),
            set(blacklisted_users),
        )

    def is_blocked(self, user_or_channel):
        if isinstance(user_or_channel, discord.abc.User):
            return user_or_channel.id in self.blacklisted_users
        return user_or_channel.id in self.blacklisted_channels

    def add_block(self, user_or_channel):
        if isinstance(user_or_channel, discord.abc.User):
            self.blacklisted_users.add(user_or_channel.id)
        else:
            self.blacklisted_channels.add(user_or_channel.id)

    def remove_block(self, user_or_channel):
        if isinstance(user_or_channel, discord.abc.User):
            self.blacklisted_users.discard(user_or_channel.id)
        else:
            self.blacklisted_channels.discard(user_or_channel.id)


class SettingsModel:
    __slots__ = (
        "sql",
        "tb_guild_settings",
        "tb_special_roles",
        "tb_tracking_blacklists",
        "guild_settings_cache",
        "roles_cache",
        "tracking_blacklist_cache",
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_guild_settings = Table(
            "guild_settings",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("prefix", Unicode, nullable=True),
            Column("max_delete_messages", SmallInteger),
            Column("warn_manual_mod_action", Boolean, default=False),
        )
        self.tb_special_roles = Table(
            "special_roles",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("member_role_id", BigInteger, nullable=True),
            Column("guest_role_id", BigInteger, nullable=True),
            Column("mute_role_id", BigInteger, nullable=True),
            Column("jail_role_id", BigInteger, nullable=True),
            # Ensures special roles aren't assigned to @everyone
            CheckConstraint(
                "member_role_id is NULL OR member_role_id != guild_id",
                name="special_role_member_not_everyone_check",
            ),
            CheckConstraint(
                "guest_role_id is NULL or guest_role_id != guild_id",
                name="special_role_guest_not_everyone_check",
            ),
            CheckConstraint(
                "mute_role_id is NULL or mute_role_id != guild_id",
                name="special_role_mute_not_everyone_check",
            ),
            CheckConstraint(
                "jail_role_id is NULL or jail_role_id != guild_id",
                name="special_role_jail_not_everyone_check",
            ),
            # Ensures Guest and punishment roles aren't the same as the Member role
            CheckConstraint(
                "guest_role_id is NULL OR guest_role_id != member_role_id",
                name="special_role_guest_not_member_check",
            ),
            CheckConstraint(
                "mute_role_id is NULL OR mute_role_id != member_role_id",
                name="special_role_mute_not_member_check",
            ),
            CheckConstraint(
                "jail_role_id is NULL OR jail_role_id != member_role_id",
                name="special_role_jail_not_member_check",
            ),
        )
        self.tb_tracking_blacklists = Table(
            "tracking_blacklists",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id"), index=True),
            Column("type", Enum(LocationType)),
            Column("data_id", BigInteger),
            UniqueConstraint(
                "guild_id", "type", "data_id", name="tracking_blacklist_uq"
            ),
            CheckConstraint(
                "type IN ('CHANNEL'::locationtype, 'USER'::locationtype)",
                name="type_is_channel_or_user_check",
            ),
        )
        self.guild_settings_cache = {}
        self.roles_cache = {}
        self.tracking_blacklist_cache = {}

        register_hook("on_guild_join", self.add_guild_settings)
        register_hook("on_guild_leave", self.remove_guild_settings)

        register_hook("on_guild_join", self.add_special_roles)
        register_hook("on_guild_leave", self.remove_special_roles)

    def add_guild_settings(self, guild):
        logger.info(
            "Adding guild settings row for new guild '%s' (%d)", guild.name, guild.id
        )
        ins = self.tb_guild_settings.insert().values(
            guild_id=guild.id,
            prefix=None,
            max_delete_messages=self.sql.max_delete_messages,
            warn_manual_mod_action=False,
        )
        self.sql.execute(ins)
        self.guild_settings_cache[guild] = GuildSettingsStorage(
            None, self.sql.max_delete_messages, False
        )

    def remove_guild_settings(self, guild):
        logger.info(
            "Removing guild settings row for departing guild '%s' (%d)",
            guild.name,
            guild.id,
        )
        delet = self.tb_guild_settings.delete().where(
            self.tb_guild_settings.c.guild_id == guild.id
        )
        self.sql.execute(delet)
        self.guild_settings_cache.pop(guild, None)

    def fetch_guild_settings(self, guild):
        logger.info("Getting guild settings for guild '%s' (%d)", guild.name, guild.id)

        sel = select(
            [
                self.tb_guild_settings.c.prefix,
                self.tb_guild_settings.c.max_delete_messages,
                self.tb_guild_settings.c.warn_manual_mod_action,
            ]
        ).where(self.tb_guild_settings.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_guild_settings(guild)

        prefix, max_delete_messages, warn_manual_mod_action = result.fetchone()
        self.guild_settings_cache[guild] = GuildSettingsStorage(
            prefix, max_delete_messages, warn_manual_mod_action
        )

    def get_prefix(self, guild):
        logger.debug("Getting prefix for guild '%s' (%d)", guild.name, guild.id)
        if guild not in self.guild_settings_cache:
            self.fetch_guild_settings(guild)

        return self.guild_settings_cache[guild].prefix

    def set_prefix(self, guild, prefix):
        logger.info(
            "Setting prefix to %r for guild '%s' (%d)", prefix, guild.name, guild.id
        )
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(prefix=prefix)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].prefix = prefix

    def get_max_delete_messages(self, guild):
        logger.info(
            "Getting maximum delete messages for guild '%s' (%d)", guild.name, guild.id
        )
        if guild not in self.guild_settings_cache:
            self.fetch_guild_settings(guild)

        return self.guild_settings_cache[guild].max_delete_messages

    def set_max_delete_messages(self, guild, max_delete_messages):
        logger.info(
            "Setting maximum delete messages to %d for guild '%s' (%d)",
            max_delete_messages,
            guild.name,
            guild.id,
        )
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(max_delete_messages=max_delete_messages)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].max_delete_messages = max_delete_messages

    def get_warn_manual_mod_action(self, guild):
        logger.info(
            "Getting warn manual mod action flag for guild '%s' (%d)",
            guild.name,
            guild.id,
        )
        if guild not in self.guild_settings_cache:
            self.fetch_guild_settings(guild)

        return self.guild_settings_cache[guild].warn_manual_mod_action

    def set_warn_manual_mod_action(self, guild, warn_manual_mod_action):
        logger.info(
            "Setting warn manual mod action flag to %d for guild '%s' (%d)",
            warn_manual_mod_action,
            guild.name,
            guild.id,
        )
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(warn_manual_mod_action=warn_manual_mod_action)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].warn_manual_mod_action = warn_manual_mod_action

    def add_special_roles(self, guild):
        logger.info(
            "Adding special roles row for new guild '%s' (%d)", guild.name, guild.id
        )
        ins = self.tb_special_roles.insert().values(
            guild_id=guild.id,
            member_role_id=None,
            guest_role_id=None,
            mute_role_id=None,
            jail_role_id=None,
        )
        self.sql.execute(ins)
        self.roles_cache[guild] = SpecialRoleStorage(guild, None, None, None, None)

    def remove_special_roles(self, guild):
        logger.info(
            "Removing special roles row for new guild '%s' (%d)", guild.name, guild.id
        )
        delet = self.tb_special_roles.delete().where(
            self.tb_special_roles.c.guild_id == guild.id
        )
        self.sql.execute(delet)
        self.roles_cache.pop(guild, None)

    def get_special_roles(self, guild):
        logger.debug("Getting special roles for guild '%s' (%d)", guild.name, guild.id)
        if guild in self.roles_cache:
            logger.debug("Special roles found in cache, returning")
            return self.roles_cache[guild]

        sel = select(
            [
                self.tb_special_roles.c.member_role_id,
                self.tb_special_roles.c.guest_role_id,
                self.tb_special_roles.c.mute_role_id,
                self.tb_special_roles.c.jail_role_id,
            ]
        ).where(self.tb_special_roles.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_special_roles(guild)
            return self.roles_cache[guild]

        member_role_id, guest_role_id, mute_role_id, jail_role_id = result.fetchone()
        roles = SpecialRoleStorage(
            guild, member_role_id, guest_role_id, mute_role_id, jail_role_id
        )
        self.roles_cache[guild] = roles
        return roles

    def set_special_roles(self, guild, **attrs):
        logger.info("Setting special role(s) for guild '%s' (%d)", guild.name, guild.id)
        assert attrs, "No roles to change"

        values = {}
        for attr, role in attrs.items():
            assert attr in ("member", "guest", "mute", "jail"), "Unknown column"
            values[f"{attr}_role_id"] = getattr(role, "id", None)

        upd = (
            self.tb_special_roles.update()
            .where(self.tb_special_roles.c.guild_id == guild.id)
            .values(values)
        )
        self.sql.execute(upd)
        self.roles_cache[guild].update(attrs)

    def add_to_tracking_blacklist(self, guild, user_or_channel):
        logger.info(
            "Adding '%s' (%d) to the tracking blacklist for guild '%s' (%d)",
            user_or_channel.name,
            user_or_channel.id,
            guild.name,
            guild.id,
        )

        block_type = (
            LocationType.USER
            if isinstance(user_or_channel, discord.abc.User)
            else LocationType.CHANNEL
        )

        ins = self.tb_tracking_blacklists.insert().values(
            guild_id=guild.id, type=block_type, data_id=user_or_channel.id
        )
        self.sql.execute(ins)
        if guild in self.tracking_blacklist_cache:
            self.tracking_blacklist_cache[guild].add_block(user_or_channel)

    def get_tracking_blacklist(self, guild):
        logger.debug(
            "Getting tracking blacklist for guild '%s' (%d)", guild.name, guild.id
        )
        if guild in self.tracking_blacklist_cache:
            logger.debug("Tracking blacklist found in cache, returning")
            return self.tracking_blacklist_cache[guild]

        sel = select(
            [self.tb_tracking_blacklists.c.type, self.tb_tracking_blacklists.c.data_id]
        ).where(self.tb_tracking_blacklists.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        blacklist = TrackingBlacklistStorage(guild, result.fetchall())
        self.tracking_blacklist_cache[guild] = blacklist
        return blacklist

    def remove_from_tracking_blacklist(self, guild, user_or_channel):
        logger.info(
            "Deleting '%s' (%d) from the tracking blacklist for guild '%s' (%d)",
            user_or_channel.name,
            user_or_channel.id,
            guild.name,
            guild.id,
        )

        block_type = (
            LocationType.USER
            if isinstance(user_or_channel, discord.abc.User)
            else LocationType.CHANNEL
        )

        delet = self.tb_tracking_blacklists.delete().where(
            self.tb_tracking_blacklists.c.guild_id == guild.id,
            self.tb_tracking_blacklists.c.type == block_type,
            self.tb_tracking_blacklists.c.data_id == user_or_channel.id,
        )
        self.sql.execute(delet)
        if guild in self.tracking_blacklist_cache:
            self.tracking_blacklist_cache[guild].remove_block(user_or_channel)
