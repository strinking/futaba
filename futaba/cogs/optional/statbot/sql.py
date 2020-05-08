#
# cogs/optional/statbot/sql.py
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
Module for abstractly interfacing with Statbot's RDBMS.
"""

import logging

from sqlalchemy import create_engine
from sqlalchemy.sql import text

from .utils import int_hash

logger = logging.getLogger(__name__)

__all__ = ["StatbotSqlHandler"]


class StatbotSqlHandler:
    __slots__ = ("db", "conn")

    def __init__(self, db_path: str):
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        logger.info("Connected to database...")

    def __del__(self):
        self.conn.close()

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)

    # Specific queries
    def message_count(self, guild, user, excluded_channels=()):
        """
        Determines how many messages a user has in the guild.
        A list of excluded channels can be specified.
        """

        logger.info(
            "Querying message count for user '%s' (%d) in guild '%s' (%d)",
            user.name,
            user.id,
            guild.name,
            guild.id,
        )

        stmt = text(
            """
            SELECT
                COUNT(message_id) AS messages,
                COUNT(edited_at) AS edited,
                COUNT(deleted_at) AS deleted
            FROM messages
            WHERE guild_id = :guild_id
                AND int_user_id = :user_id
                AND channel_id NOT IN :excluded_channel_ids
        """
        )

        excluded_channel_ids = tuple(channel.id for channel in excluded_channels)
        result = self.conn.execute(
            stmt,
            guild_id=guild.id,
            user_id=int_hash(user.id),
            excluded_channel_ids=excluded_channel_ids or (0,),
        )

        message_count, edited_count, deleted_count = result.fetchone()
        return message_count, edited_count, deleted_count
