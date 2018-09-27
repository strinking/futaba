#
# sql/models/alias.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
A model for storing alias information reported by the 'Alias' cog.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, DateTime, LargeBinary, String, Table, Unicode
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'AliasHistoryModel',
]

class AliasHistoryModel:
    __slots__ = (
        'sql',
        'tb_alias_avatars',
        'tb_alias_usernames',
        'tb_alias_nicknames',
        'tb_alias_possible_alts',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_alias_avatars = Table('alias_avatars', meta,
                Column('user_id', BigInteger, primary_key=True),
                Column('timestamp', DateTime, primary_key=True),
                Column('avatar', LargeBinary),
                Column('avatar_ext', String))
        self.tb_alias_usernames = Table('alias_usernames', meta,
                Column('user_id', BigInteger, primary_key=True),
                Column('timestamp', DateTime, primary_key=True),
                Column('username', Unicode))
        self.tb_alias_nicknames = Table('alias_nicknames', meta,
                Column('user_id', BigInteger, primary_key=True),
                Column('timestamp', DateTime, primary_key=True),
                Column('nickname', Unicode))
        self.tb_alias_possible_alts = Table('alias_possible_alts', meta,
                Column('guild_id', BigInteger, ForeignKey('guilds.guild_id')),
                Column('lower_user_id', BigInteger),
                Column('higher_user_id', BigInteger),
                CheckConstraint('lower_user_id < high_user_id', name='alias_possible_alts_check'),
                UniqueConstraint('guild_id', 'lower_user_id', 'higher_user_id',
                    name='alias_possible_alts_uq'))

    def add_avatar(self, user, timestamp, avatar, ext):
        logger.info("Adding user avatar update for '%s' (%d)", user.name, user.id)
        ins = self.tb_alias_avatars \
                .insert() \
                .values(user_id=user.id, timestamp=timestamp, avatar=avatar, avatar_ext=ext)
        self.sql.execute(ins)

    def add_username(self, user, timestamp, username):
        logger.info("Adding username update for '%s', now '%s' (%d)",
                user.name, username, user.id)
        ins = self.tb_alias_usernames \
                .insert() \
                .values(user_id=user.id, timestamp=timestamp, username=username)
        self.sql.execute(ins)

    def add_nickname(self, user, timestamp, nickname):
        logger.info("Adding nickname update for '%s', now '%s' (%d)",
                user.display_name, nickname, user.id)
        ins = self.tb_alias_nicknames \
                .insert() \
                .values(user_id=user.id, timestamp=timestamp, nickname=nickname)
        self.sql.execute(ins)

    def add_alias(self, guild, first_user, second_user):
        logger.info("Adding alias relationship: '%s' (%d) <--> '%s' (%d)",
                first_user.name, first_user.id, second_user.name, second_user.id)
        if first_user.id > second_user.id:
            first_user, second_user = second_user, first_user

        ins = self.tb_alias_possible_alts \
                .insert() \
                .values(guild_id=guild.id, lower_user_id=first_user.id, higher_user_id=second_user.id)

        try:
            self.sql.execute(ins)
        except IntegrityError:
            pass

    def get_aliases(self, user, avatar_limit=4, username_limit=8, nickname_limit=12):
        logger.info("Getting aliases of user '%s' (%d)", user.name, user.id)
        sel = select([
                    self.tb_alias_avatars.c.avatar,
                    self.tb_alias_avatars.c.avatar_ext,
                    self.tb_alias_avatars.c.timestamp,
                ]) \
                .where(self.tb_alias_avatars.c.user_id == user.id) \
                .order_by(self.tb_alias_avatars.c.timestamp) \
                .limit(avatar_limit)
        avatars = list(self.sql.execute(sel))

        sel = select([self.tb_alias_usernames.c.username, self.tb_alias_usernames.c.timestamp]) \
                .where(self.tb_alias_usernames.c.user_id == user.id) \
                .order_by(self.tb_alias_usernames.c.timestamp) \
                .limit(username_limit)
        usernames = list(self.sql.execute(sel))

        sel = select([self.tb_alias_nicknames.c.nickname, self.tb_alias_nicknames.c.timestamp]) \
                .where(self.tb_alias_nicknames.c.user_id == user.id) \
                .order_by(self.tb_alias_nicknames.c.timestamp) \
                .limit(nickname_limit)
        nicknames = list(self.sql.execute(sel))

        return avatars, usernames, nicknames
