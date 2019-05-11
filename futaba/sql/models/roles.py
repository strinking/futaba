#
# sql/models/roles.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
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
from sqlalchemy import ARRAY, BigInteger, Column, Table
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["RolesModel"]


class RolesModel:
    __slots__ = (
        "sql",
        "tb_assignable_roles",
        "tb_role_command_channels",
        "tb_saved_roles",
        "tb_can_reapply_roles",
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
            UniqueConstraint("guild_id", "role_id", name="assignable_roles_uq"),
        )
        self.tb_role_command_channels = Table(
            "role_command_channels",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("channel_id", BigInteger),
            UniqueConstraint("guild_id", "channel_id", name="role_command_channels_uq"),
        )
        self.tb_saved_roles = Table(
            "saved_roles",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("user_id", BigInteger, primary_key=True),
            Column("role_ids", ARRAY(BigInteger)),
        )
        self.tb_can_reapply_roles = Table(
            "can_reapply_roles",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("role_id", BigInteger),
            UniqueConstraint("guild_id", "role_id", name="can_reapply_roles_uq"),
        )
        self.roles_cache = {}
        self.channels_cache = {}

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

    def get_role_command_channels(self, guild):
        logger.info(
            "Getting all role command channels for guild '%s' (%d)",
            guild.name,
            guild.id,
        )

        if guild in self.channels_cache:
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

    def add_role_command_channel(self, guild, channel):
        logger.info(
            "Adding role command channel for guild '%s' (%d)", guild.name, guild.id
        )
        assert guild == channel.guild
        ins = self.tb_role_command_channels.insert().values(
            guild_id=guild.id, channel_id=channel.id
        )
        self.sql.execute(ins)
        self.channels_cache[guild].add(channel)

    def remove_role_command_channel(self, guild, channel):
        logger.info(
            "Removing role command channel for guild '%s' (%d)", guild.name, guild.id
        )
        assert guild == channel.guild
        delet = self.tb_role_command_channels.delete().where(
            and_(
                self.tb_role_command_channels.c.guild_id == guild.id,
                self.tb_role_command_channels.c.channel_id == channel.id,
            )
        )
        result = self.sql.execute(delet)
        assert result.rowcount in (0, 1), "Multiple rows deleted"

        if result.rowcount:
            self.channels_cache[guild].remove(channel)

    def add_saved_roles(self, member):
        logger.info(
            "Adding saved roles list for '%s' (%d) in guild '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )
        ins = self.tb_saved_roles.insert().values(
            guild_id=member.guild.id,
            user_id=member.id,
            role_ids=[role.id for role in member.roles],
        )
        self.sql.execute(ins)

    def get_saved_roles(self, member):
        logger.info(
            "Getting saved roles for '%s' (%d) in guild '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )
        sel = select([self.tb_saved_roles.c.role_ids]).where(
            and_(
                self.tb_saved_roles.c.guild_id == member.guild.id,
                self.tb_saved_roles.c.user_id == member.id,
            )
        )
        result = self.sql.execute(sel)

        if not result.rowcount:
            return []

        roles = []
        (role_ids,) = result.fetchone()
        for role_id in role_ids:
            role = discord.utils.get(member.guild.roles, id=role_id)
            if role is not None:
                roles.append(role)
        return roles

    def update_saved_roles(self, member):
        logger.info(
            "Updating saved roles for '%s' (%d) in guild '%s' (%d): [%s]",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
            ", ".join(role.name for role in member.roles),
        )

        sel = select([None]).where(
            and_(
                self.tb_saved_roles.c.guild_id == member.guild.id,
                self.tb_saved_roles.c.user_id == member.id,
            )
        )
        result = self.sql.execute(sel)

        # Cannot UPDATE, must do first INSERT
        if not result.rowcount:
            self.add_saved_roles(member)
            return

        upd = (
            self.tb_saved_roles.update()
            .where(
                and_(
                    self.tb_saved_roles.c.guild_id == member.guild.id,
                    self.tb_saved_roles.c.user_id == member.id,
                )
            )
            .values(
                guild_id=member.guild.id,
                user_id=member.id,
                role_ids=[role.id for role in member.roles],
            )
        )
        self.sql.execute(upd)
