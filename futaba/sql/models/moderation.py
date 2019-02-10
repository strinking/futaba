#
# sql/models/moderation.py
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
SQL model for storing information about present moderation events.
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

__all__ = ["ModerationModel"]


class ModerationModel:
    __slots__ = ("sql", "tb_removed_other_roles")

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_removed_other_roles = Table(
            "removed_other_roles",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("user_id", BigInteger),
            Column("keep_role", BigInteger),
            Column("other_roles", ARRAY(BigInteger)),
            UniqueConstraint("guild_id", "user_id", name="uq_removed_other_roles"),
        )

    def get_other_roles(self, member):
        logger.debug(
            "Determining if there are other roles (in punishment) for member '%s' (%d) in guild '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        sel = select(
            [
                self.tb_removed_other_roles.c.keep_role,
                self.tb_removed_other_roles.c.other_roles,
            ]
        ).where(
            and_(
                self.tb_removed_other_roles.c.guild_id == member.guild.id,
                self.tb_removed_other_roles.c.user_id == member.id,
            )
        )
        result = self.sql.execute(sel)
        if result.rowcount:
            keep_role_id, other_role_ids = result.fetchone()
            keep_role = discord.utils.get(member.guild.roles, id=keep_role_id)
            other_roles = [
                discord.utils.get(member.guild.roles, id=id) for id in other_role_ids
            ]
            return True, keep_role, other_roles
        else:
            return False, None, None

    async def remove_other_roles(self, member, keep_role, reason):
        logger.info(
            "Removing member '%s' (%d)'s roles in guild '%s' (%d) to just '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
            keep_role.name,
            keep_role.id,
        )

        sel = select(
            [
                self.tb_removed_other_roles.c.keep_role,
                self.tb_removed_other_roles.c.other_roles,
            ]
        ).where(
            and_(
                self.tb_removed_other_roles.c.guild_id == member.guild.id,
                self.tb_removed_other_roles.c.user_id == member.id,
            )
        )
        result = self.sql.execute(sel)
        if result.rowcount == 1:
            # Update only the keep role, leave the others alone
            upd = (
                self.tb_removed_other_roles.update()
                .values(keep_role=keep_role.id)
                .where(
                    and_(
                        self.tb_removed_other_roles.c.guild_id == member.guild.id,
                        self.tb_removed_other_roles.c.user_id == member.id,
                    )
                )
            )
            self.sql.execute(upd)
            return

        # Add new removed_other_roles entry
        other_roles = [role.id for role in member.roles if role != keep_role]
        ins = self.tb_removed_other_roles.insert().values(
            guild_id=member.guild.id,
            user_id=member.id,
            keep_role=keep_role.id,
            other_roles=other_roles,
        )
        self.sql.execute(ins)

        # Replaces all the member's roles with just keep_role
        await member.edit(roles=[keep_role], reason=reason)

    async def restore_other_roles(self, member, reason):
        logger.info(
            "Restoring member '%s' (%d)'s roles in guild '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        sel = select([self.tb_removed_other_roles.c.other_roles]).where(
            and_(
                self.tb_removed_other_roles.c.guild_id == member.guild.id,
                self.tb_removed_other_roles.c.user_id == member.id,
            )
        )
        result = self.sql.execute(sel)
        if result.rowcount == 0:
            return KeyError(member)

        other_roles = []
        other_role_ids, = result.fetchone()
        for role_id in other_role_ids:
            role = discord.utils.get(member.guild.roles, id=role_id)
            if role is not None:
                other_roles.append(role)

        # Add all of other_roles and remove keep_role, the same as just setting to other_roles
        await member.edit(roles=other_roles, reason=reason)

        # Now that it's restored, delete the row to not mess with others
        delet = self.tb_removed_other_roles.delete().where(
            and_(
                self.tb_removed_other_roles.c.guild_id == member.guild.id,
                self.tb_removed_other_roles.c.user_id == member.id,
            )
        )
        result = self.sql.execute(delet)
        assert result.rowcount == 1, "Row disappeared or wasn't deleted"
