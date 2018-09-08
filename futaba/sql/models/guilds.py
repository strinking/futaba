#
# sql/models/guilds.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Stores guilds the bot was a member of during its last run.
If this list deviates from which guilds it is currently in, then
setup or teardown for the appropriate guilds is run.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import namedtuple

from sqlalchemy import BigInteger, Column, Table
from sqlalchemy import ForeignKey
from sqlalchemy.sql import select

from ..hooks import run_hooks

Column = functools.partial(Column, nullable=False)
FakeGuild = namedtuple('FakeGuild', ('id', 'name'))
logger = logging.getLogger(__name__)

__all__ = [
    'GuildsModel',
]

class GuildsModel:
    __slots__ = (
        'sql',
        'tb_guilds',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_guilds = Table('guilds', meta,
                Column('guild_id', BigInteger, primary_key=True))

    # Note: Do NOT use @on_guild_join or @on_guild_leave here, this is
    # where those hooks are invoked. This method itself is called by the
    # client on an actual guild join or leave event.

    def add_guild(self, guild):
        logger.info("Adding guild '%s' (%d) to guilds list", guild.name, guild.id)
        ins = self.tb_guilds \
                .insert() \
                .values(guild_id=guild.id)
        self.sql.execute(ins)
        run_hooks('on_guild_join', guild)

    def remove_guild(self, guild):
        logger.info("Removing guild '%s' (%d) from guilds list", guild.name, guild.id)
        run_hooks('on_guild_leave', guild)
        delet = self.tb_guilds \
                .delete() \
                .where(guild_id=guild.id)
        self.sql.execute(delet)

    def get_guilds(self, bot):
        logger.info("Fetching guilds currently in database")
        sel = select([self.tb_guilds.c.guild_id])
        result = self.sql.execute(sel)

        get_guild = lambda id: bot.get_guild(id) or FakeGuild(id=id, name=f'<Guild id {id}>')
        return (get_guild(guild_id) for guild_id, in result.fetchmany())
