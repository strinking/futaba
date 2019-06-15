#
# cogs/optional/statbot/sql.py
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
    def message_count(self, guild, user, excluded_channels=None, included_channels=None):
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

        if excluded_channels and included_channels:
            raise ValueError("both included_channels and excluded_channels present")
        rest_of_stmt = ""
        channel_ids = ()

        if excluded_channels:
            rest_of_stmt = "AND channel_id NOT IN :channel_ids"
            channel_ids = tuple(channel.id for channel in excluded_channels)

        if included_channels:
            rest_of_stmt = "AND channel_id IN :channel_ids"
            channel_ids = tuple(channel.id for channel in included_channels)

        stmt = text(
            f"""
            SELECT
                COUNT(message_id) AS messages,
                COUNT(edited_at) AS edited,
                COUNT(deleted_at) AS deleted
            FROM messages
            WHERE guild_id = :guild_id
                AND int_user_id = :user_id
                {rest_of_stmt}
        """
        )

        result = self.conn.execute(
            stmt,
            guild_id=guild.id,
            user_id=int_hash(user.id),
            channel_ids=channel_ids,
        )

        message_count, edited_count, deleted_count = result.fetchone()
        return message_count, edited_count, deleted_count
