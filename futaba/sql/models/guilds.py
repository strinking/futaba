#
# sql/models/guilds.py
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
Stores guilds the bot was a member of during its last run.
If this list deviates from which guilds it is currently in, then
setup or teardown for the appropriate guilds is run.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import namedtuple

from sqlalchemy import Boolean, BigInteger, Column, Table
from sqlalchemy.sql import select

from ..hooks import run_hooks

Column = functools.partial(Column, nullable=False)
FakeGuild = namedtuple("FakeGuild", ("id", "name"))
logger = logging.getLogger(__name__)

__all__ = ["GuildsModel"]


class GuildsModel:
    __slots__ = ("sql", "tb_guilds")

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_guilds = Table(
            "guilds",
            meta,
            Column("guild_id", BigInteger, primary_key=True),
            Column("active", Boolean, default=True),
        )

    # Note: Do NOT register the on_guild_join/on_guild_leave hooks here,
    # as this is where those hooks are invoked. This method itself is
    # called by the client on an actual guild join or leave event.

    def activate_guild(self, guild):
        logger.info("Adding guild '%s' (%d) to guilds list", guild.name, guild.id)

        if guild.id in self.get_guild_ids():
            upd = (
                self.tb_guilds.update()
                .values(active=True)
                .where(self.tb_guilds.c.guild_id == guild.id)
            )
            self.sql.execute(upd)
        else:
            ins = self.tb_guilds.insert().values(guild_id=guild.id)
            self.sql.execute(ins)

        run_hooks("on_guild_join", guild)

    def deactivate_guild(self, guild):
        logger.info("Removing guild '%s' (%d) from guilds list", guild.name, guild.id)
        run_hooks("on_guild_leave", guild)

        upd = (
            self.tb_guilds.update()
            .values(active=False)
            .where(self.tb_guilds.c.guild_id == guild.id)
        )
        self.sql.execute(upd)

        delet = self.tb_guilds.delete().where(self.tb_guilds.c.guild_id == guild.id)
        self.sql.execute(delet)

    def get_guild_ids(self):
        logger.info("Fetching guilds currently in database")
        sel = select([self.tb_guilds.c.guild_id])
        result = self.sql.execute(sel)

        return (guild_id for guild_id, in result.fetchall())

    @staticmethod
    def _get_guild(bot, guild_id):
        return bot.get_guild(guild_id) or FakeGuild(
            id=guild_id, name=f"<Guild id {guild_id}>"
        )

    def migrate(self, bot):
        migrated_guild_ids = frozenset(self.get_guild_ids())
        current_guild_ids = frozenset(guild.id for guild in bot.guilds)

        logger.info(
            "Migrating guilds: [%s] -> [%s]",
            ", ".join(map(str, migrated_guild_ids)),
            ", ".join(map(str, current_guild_ids)),
        )
        logger.debug("Running insertions...")
        with self.sql.transaction():
            for guild_id in current_guild_ids - migrated_guild_ids:
                guild = self._get_guild(bot, guild_id)
                self.activate_guild(guild)

        logger.debug("Running deletions...")
        with self.sql.transaction():
            for guild_id in migrated_guild_ids - current_guild_ids:
                guild = self._get_guild(bot, guild_id)
                self.deactivate_guild(guild)
