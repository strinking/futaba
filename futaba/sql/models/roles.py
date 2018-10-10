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
from collections import defaultdict

import discord
from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["SelfAssignableRolesModel"]


class SelfAssignableRolesModel:
    __slots__ = ("sql", "tb_assignable_roles", "roles_cache")

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_assignable_roles = Table(
            "assignable_roles",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("role_id", BigInteger),
            UniqueConstraint("role_id", name="assignable_roles_uq"),
        )
        self.roles_cache = defaultdict(set)

        register_hook("on_guild_leave", self.remove_all_assignable_roles)

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

        for role_id in result.fetchall():
            role = discord.utils.get(guild.roles, id=role_id)
            if role is not None:
                self.roles_cache[guild].add(role)

        return self.roles_cache[guild]

    def add_assignable_role(self, guild, role):
        logger.info("Adding assignable role for guild '%s' (%d)", guild.name, guild.id)
        ins = self.tb_assignable_roles.insert().values(
            guild_id=guild.id, role_id=role.id
        )
        self.sql.execute(ins)

    def remove_assignable_role(self, guild, role):
        logger.info(
            "Removing assignable role for guild '%s' (%d)", guild.name, guild.id
        )
        delet = self.tb_assignable_roles.delete().where(
            and_(
                self.tb_assignable_roles.c.guild_id == guild.id,
                self.tb_assignable_roles.c.role_id == role.id,
            )
        )
        result = self.sql.execute(delet)
        assert result.rowcount in (0, 1), "Multiple rows deleted"
