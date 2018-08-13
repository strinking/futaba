#
# sql/settings.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import functools
import logging

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from .hooks import on_guild_join, on_guild_leave
from .transaction import Transaction

'''
Has the model for managing persistent bot settings.
'''

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'SettingsModel',
]

class SettingsModel:
    __slots__ = (
        'tb_prefixes',
    )

    def __init__(self, meta):
        self.tb_prefixes = Table('prefixes', meta,
                Column('guild_id', BigInteger, primary_key=True),
                Column('prefix', Unicode, nullable=True))

    @on_guild_join
    def add_prefix(self, trans, guild):
        logger.info("Adding prefix row for new guild '%s' (%d)", guild.name, guild.id)
        ins = self.tb_prefixes \
                .insert() \
                .values(
                    guild_id=guild.id,
                    prefix=None,
                )
        trans.execute(ins)

    @on_guild_leave
    def del_prefix(self, trans, guild):
        logger.info("Removing prefix row for departing guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_prefixes \
                    .delete() \
                    .where(self.tb_prefixes.c.guild_id == guild.id)
        trans.execute(delet)

    def get_prefix(self, trans, guild):
        sel = select([self.tb_prefixes]) \
            .where(self.tb_prefixes.c.guild_id == guild.id)
        result = trans.execute(sel)

        if result.rowcount:
            _, prefix = result.fetchone()
            return prefix
        else:
            return None

    def set_prefix(self, trans, guild, prefix):
        upd = self.tb_prefixes \
                .update() \
                .where(self.tb_prefixes.c.guild_id == guild.id) \
                .values(prefix=prefix)
        trans.execute(upd)
