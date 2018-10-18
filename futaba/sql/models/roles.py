#
# sql/models/roles.py
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
Model for storing the configured self-assignable roles within a guild.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

import discord
from sqlalchemy import and_
from sqlalchemy import BigInteger, Column, Table
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["SelfAssignableRolesModel"]


class SelfAssignableRolesModel:
    __slots__ = (
        "sql",
        "tb_assignable_roles",
        "tb_role_command_channels",
        "roles_cache",
        "channels_cache",
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_assignable_roles = Table(
            "assignable_roles",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("role_id", BigInteger),
            UniqueConstraint("role_id", name="assignable_roles_uq"),
        )
        self.tb_role_command_channels = Table(
            "role_command_channels",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("channel_id", BigInteger),
            UniqueConstraint("guild_id", "channel_id", name="role_command_channels_uq"),
        )
        self.roles_cache = {}
        self.channels_cache = {}

        register_hook("on_guild_leave", self.remove_all_assignable_roles)
        register_hook("on_guild_leave", self.remove_all_role_command_channels)

    def remove_all_assignable_roles(self, guild):
        logger.info(
            "Remove all assignable roles for guild '%s' (%d)", guild.name, guild.id
        )
        delet = self.tb_assignable_roles.delete().where(
            self.tb_assignable_roles.c.guild_id == guild.id
        )
        self.sql.execute(delet)
        self.roles_cache.pop(guild, None)

    def get_assignable_roles(self, guild):
        logger.info(
            "Getting all assignable roles for guild '%s' (%d)", guild.name, guild.id
        )

        if guild in self.roles_cache:
            logger.debug("Found roles in cache, returning")
            return self.roles_cache[guild]

        sel = select([self.tb_assignable_roles.c.role_id]).where(
            self.tb_assignable_roles.c.guild_id == guild.id
        )
        result = self.sql.execute(sel)

        roles = set()
        for (role_id,) in result.fetchall():
            role = discord.utils.get(guild.roles, id=role_id)
            if role is not None:
                roles.add(role)

        self.roles_cache[guild] = roles
        return roles

    def add_assignable_role(self, guild, role):
        logger.info("Adding assignable role for guild '%s' (%d)", guild.name, guild.id)
        assert guild == role.guild
        ins = self.tb_assignable_roles.insert().values(
            guild_id=guild.id, role_id=role.id
        )
        self.sql.execute(ins)
        self.roles_cache[guild].add(role)

    def remove_assignable_role(self, guild, role):
        logger.info(
            "Removing assignable role for guild '%s' (%d)", guild.name, guild.id
        )
        assert guild == role.guild
        delet = self.tb_assignable_roles.delete().where(
            and_(
                self.tb_assignable_roles.c.guild_id == guild.id,
                self.tb_assignable_roles.c.role_id == role.id,
            )
        )
        result = self.sql.execute(delet)
        assert result.rowcount in (0, 1), "Multiple rows deleted"

        if result.rowcount:
            self.roles_cache[guild].remove(role)

    def remove_all_role_command_channels(self, guild):
        logger.info(
            "Remove all role command channels for guild '%s' (%d)", guild.name, guild.id
        )
        delet = self.tb_role_command_channels.delete().where(
            self.tb_role_command_channels.c.guild_id == guild.id
        )
        self.sql.execute(delet)

    def get_role_command_channels(self, guild):
        logger.info(
            "Getting all role command channels for guild '%s' (%d)",
            guild.name,
            guild.id,
        )

        if guild in self.channels_cache[guild]:
            logger.debug("Found channels in cache, returning")
            return self.channels_cache[guild]

        sel = select([self.tb_role_command_channels.c.channel_id]).where(
            self.tb_role_command_channels.c.guild_id == guild.id
        )
        result = self.sql.execute(sel)

        channels = set()
        for (channel_id,) in result.fetchall():
            chan = discord.utils.get(guild.text_channels, id=channel_id)
            if chan is not None:
                channels.add(chan)

        self.channels_cache[guild] = channels
        return channels
