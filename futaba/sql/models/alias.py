#
# sql/models/alias.py
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
A model for storing alias information reported by the 'Alias' cog.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import deque

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, DateTime, LargeBinary, String, Table, Unicode
from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["AliasHistoryModel"]


class AliasHistoryModel:
    __slots__ = (
        "sql",
        "tb_alias_avatars",
        "tb_alias_usernames",
        "tb_alias_nicknames",
        "tb_alias_possible_alts",
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_alias_avatars = Table(
            "alias_avatars",
            meta,
            Column("user_id", BigInteger, primary_key=True),
            Column("timestamp", DateTime, primary_key=True),
            Column("avatar", LargeBinary),
            Column("avatar_ext", String),
        )
        self.tb_alias_usernames = Table(
            "alias_usernames",
            meta,
            Column("user_id", BigInteger, primary_key=True),
            Column("timestamp", DateTime, primary_key=True),
            Column("username", Unicode),
        )
        self.tb_alias_nicknames = Table(
            "alias_nicknames",
            meta,
            Column("user_id", BigInteger, primary_key=True),
            Column("timestamp", DateTime, primary_key=True),
            Column("nickname", Unicode),
        )
        self.tb_alias_possible_alts = Table(
            "alias_possible_alts",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("lower_user_id", BigInteger),
            Column("higher_user_id", BigInteger),
            CheckConstraint(
                "lower_user_id < higher_user_id", name="alias_possible_alts_check"
            ),
            UniqueConstraint(
                "guild_id",
                "lower_user_id",
                "higher_user_id",
                name="alias_possible_alts_uq",
            ),
        )

    def add_avatar(self, user, timestamp, avatar, ext):
        logger.info("Adding user avatar update for '%s' (%d)", user.name, user.id)
        ins = self.tb_alias_avatars.insert().values(
            user_id=user.id,
            timestamp=timestamp,
            avatar=avatar.getbuffer().tobytes(),
            avatar_ext=ext,
        )
        self.sql.execute(ins)

    def add_username(self, user, timestamp, username):
        logger.info(
            "Adding username update for '%s', now '%s' (%d)",
            user.name,
            username,
            user.id,
        )
        ins = self.tb_alias_usernames.insert().values(
            user_id=user.id, timestamp=timestamp, username=username
        )
        self.sql.execute(ins)

    def add_nickname(self, user, timestamp, nickname):
        logger.info(
            "Adding nickname update for '%s', now '%s' (%d)",
            user.display_name,
            nickname,
            user.id,
        )
        ins = self.tb_alias_nicknames.insert().values(
            user_id=user.id, timestamp=timestamp, nickname=nickname
        )
        self.sql.execute(ins)

    def add_possible_alt(self, guild, first_user, second_user):
        logger.info(
            "Adding possible alt relationship: '%s' (%d) <--> '%s' (%d)",
            first_user.name,
            first_user.id,
            second_user.name,
            second_user.id,
        )

        if first_user.id > second_user.id:
            first_user, second_user = second_user, first_user

        ins = self.tb_alias_possible_alts.insert().values(
            guild_id=guild.id,
            lower_user_id=first_user.id,
            higher_user_id=second_user.id,
        )

        try:
            self.sql.execute(ins)
        except IntegrityError as error:
            logger.debug("Got integrity error, possibly double insert", exc_info=error)

    def all_delete_possible_alts(self, guild, user):
        logger.info(
            "Removing all possible alt relationships for '%s' (%d)", user.name, user.id
        )
        alt_user_ids = self.get_alt_user_ids(guild, [user.id])
        delet = self.tb_alias_possible_alts.delete().where(
            and_(
                self.tb_alias_possible_alts.c.guild_id == guild.id,
                or_(
                    self.tb_alias_possible_alts.c.lower_user_id.in_(alt_user_ids),
                    self.tb_alias_possible_alts.c.higher_user_id.in_(alt_user_ids),
                ),
            )
        )
        self.sql.execute(delet)

    def get_aliases(
        self, guild, user, avatar_limit=4, username_limit=8, nickname_limit=12
    ):
        logger.info("Getting aliases of user '%s' (%d)", user.name, user.id)
        sel = (
            select(
                [
                    self.tb_alias_avatars.c.avatar,
                    self.tb_alias_avatars.c.avatar_ext,
                    self.tb_alias_avatars.c.timestamp,
                ]
            )
            .where(self.tb_alias_avatars.c.user_id == user.id)
            .order_by(self.tb_alias_avatars.c.timestamp)
            .limit(avatar_limit)
        )
        result = self.sql.execute(sel)
        avatars = list(result)

        sel = (
            select(
                [
                    self.tb_alias_usernames.c.username,
                    self.tb_alias_usernames.c.timestamp,
                ]
            )
            .where(self.tb_alias_usernames.c.user_id == user.id)
            .order_by(self.tb_alias_usernames.c.timestamp)
            .limit(username_limit)
        )
        result = self.sql.execute(sel)
        usernames = list(result)

        sel = (
            select(
                [
                    self.tb_alias_nicknames.c.nickname,
                    self.tb_alias_nicknames.c.timestamp,
                ]
            )
            .where(self.tb_alias_nicknames.c.user_id == user.id)
            .order_by(self.tb_alias_nicknames.c.timestamp)
            .limit(nickname_limit)
        )
        result = self.sql.execute(sel)
        nicknames = list(result)

        alt_user_ids = self.get_alt_user_ids(guild, [user.id])
        return avatars, usernames, nicknames, alt_user_ids

    def get_alias_names(self, guild, user, username_limit=6, nickname_limit=6):
        logger.info("Getting alias names of user '%s' (%d)", user.name, user.id)

        # Basically get_aliases() but only usernames and nicknames. The other queries
        # are relatively expensive, and if they're not needed, they shouldn't be run.

        sel = (
            select(
                [
                    self.tb_alias_usernames.c.username,
                    self.tb_alias_usernames.c.timestamp,
                ]
            )
            .where(self.tb_alias_usernames.c.user_id == user.id)
            .order_by(self.tb_alias_usernames.c.timestamp)
            .limit(username_limit)
        )
        result = self.sql.execute(sel)
        usernames = list(result)

        sel = (
            select(
                [
                    self.tb_alias_nicknames.c.nickname,
                    self.tb_alias_nicknames.c.timestamp,
                ]
            )
            .where(self.tb_alias_nicknames.c.user_id == user.id)
            .order_by(self.tb_alias_nicknames.c.timestamp)
            .limit(nickname_limit)
        )
        result = self.sql.execute(sel)
        nicknames = list(result)

        return usernames, nicknames

    def get_alt_user_ids(self, guild, starting_user_ids):
        logger.info("Iteratively fetching all chained user alt connections.")
        assert starting_user_ids, "No starting user IDs"
        to_check = deque(starting_user_ids)
        alt_user_ids = set()
        while to_check:
            user_id = to_check.pop()
            sel = select(
                [
                    self.tb_alias_possible_alts.c.lower_user_id,
                    self.tb_alias_possible_alts.c.higher_user_id,
                ]
            ).where(
                and_(
                    self.tb_alias_possible_alts.c.guild_id == guild.id,
                    or_(
                        self.tb_alias_possible_alts.c.lower_user_id == user_id,
                        self.tb_alias_possible_alts.c.higher_user_id == user_id,
                    ),
                )
            )
            result = self.sql.execute(sel)
            for first_id, second_id in result:
                if first_id != user_id:
                    alt_user_id = first_id
                else:
                    alt_user_id = second_id

                if alt_user_id not in alt_user_ids:
                    to_check.append(alt_user_id)
                    alt_user_ids.add(alt_user_id)
        return alt_user_ids
