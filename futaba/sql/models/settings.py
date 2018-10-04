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

import functools
import logging

import discord
from sqlalchemy import BigInteger, Column, Table, Unicode
from sqlalchemy import CheckConstraint, ForeignKey, SmallInteger
from sqlalchemy.sql import select

from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["SettingsModel"]


class GuildSettingsStorage:
    __slots__ = ("prefix", "max_delete_messages")

    def __init__(self, prefix, max_delete_messages):
        self.prefix = prefix
        self.max_delete_messages = max_delete_messages


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


class SettingsModel:
    __slots__ = (
        "sql",
        "tb_guild_settings",
        "tb_special_roles",
        "guild_settings_cache",
        "roles_cache",
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
        self.guild_settings_cache = {}
        self.roles_cache = {}

        register_hook("on_guild_join", self.add_guild_settings)
        register_hook("on_guild_leave", self.del_guild_settings)

        register_hook("on_guild_join", self.add_special_roles)
        register_hook("on_guild_leave", self.del_special_roles)

    def add_guild_settings(self, guild):
        logger.info(
            "Adding guild settings row for new guild '%s' (%d)", guild.name, guild.id
        )
        ins = self.tb_guild_settings.insert().values(
            guild_id=guild.id,
            prefix=None,
            max_delete_messages=self.sql.max_delete_messages,
        )
        self.sql.execute(ins)
        self.guild_settings_cache[guild] = GuildSettingsStorage(
            None, self.sql.max_delete_messages
        )

    def del_guild_settings(self, guild):
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
            ]
        ).where(self.tb_guild_settings.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_guild_settings(guild)

        prefix, max_delete_messages = result.fetchone()
        self.guild_settings_cache[guild] = GuildSettingsStorage(
            prefix, max_delete_messages
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

    def del_special_roles(self, guild):
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
