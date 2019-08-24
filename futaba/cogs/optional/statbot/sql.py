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

import discord
from sqlalchemy import create_engine, func
from sqlalchemy import and_, not_, case
from sqlalchemy import ARRAY, Boolean, BigInteger, Column, DateTime, Enum
from sqlalchemy import Integer, JSON, SmallInteger, String, Table, Unicode, UnicodeText
from sqlalchemy import ForeignKey, MetaData
from sqlalchemy.sql import select, text

from .utils import int_hash

logger = logging.getLogger(__name__)

__all__ = ["StatbotSqlHandler"]


class StatbotSqlHandler:
    __slots__ = (
        "db",
        "conn",
        "tb_messages",
        "tb_channels",
        "tb_channel_categories",
        "tb_guilds",
        "tb_users",
    )

    def __init__(self, db_path: str):
        logger.info("Opening to database...")
        self.db = create_engine(db_path)
        self.conn = self.db.connect()

        meta = MetaData(self.db)
        self.tb_messages = Table(
            "messages",
            meta,
            Column("message_id", BigInteger, primary_key=True),
            Column("created_at", DateTime),
            Column("edited_at", DateTime, nullable=True),
            Column("deleted_at", DateTime, nullable=True),
            Column("message_type", Enum(discord.MessageType)),
            Column("system_content", UnicodeText),
            Column("content", UnicodeText),
            Column("embeds", JSON),
            Column("attachments", SmallInteger),
            Column("webhook_id", BigInteger, nullable=True),
            Column("int_user_id", BigInteger),
            Column("channel_id", BigInteger, ForeignKey("channels.channel_id")),
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
        )

        self.tb_channels = Table(
            "channels",
            meta,
            Column("channel_id", BigInteger, primary_key=True),
            Column("name", String),
            Column("is_nsfw", Boolean),
            Column("is_deleted", Boolean),
            Column("position", SmallInteger),
            Column("topic", UnicodeText, nullable=True),
            Column("changed_roles", ARRAY(BigInteger)),
            Column(
                "category_id",
                BigInteger,
                ForeignKey("channel_categories.category_id"),
                nullable=True,
            ),
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
        )

        self.tb_channel_categories = Table(
            "channel_categories",
            meta,
            Column("category_id", BigInteger, primary_key=True),
            Column("name", Unicode),
            Column("position", SmallInteger),
            Column("is_deleted", Boolean),
            Column("is_nsfw", Boolean),
            Column("changed_roles", ARRAY(BigInteger)),
            Column(
                "parent_category_id",
                BigInteger,
                ForeignKey("channel_categories.category_id"),
                nullable=True,
            ),
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
        )

        self.tb_guilds = Table(
            "guilds",
            meta,
            Column("guild_id", BigInteger, primary_key=True),
            Column("int_owner_id", BigInteger, ForeignKey("users.int_user_id")),
            Column("name", Unicode),
            Column("icon", String),
            Column("voice_region", Enum(discord.VoiceRegion)),
            Column("afk_channel_id", BigInteger, nullable=True),
            Column("afk_timeout", Integer),
            Column("mfa", Boolean),
            Column("verification_level", Enum(discord.VerificationLevel)),
            Column("explicit_content_filter", Enum(discord.ContentFilter)),
            Column("features", ARRAY(String)),
            Column("splash", String, nullable=True),
        )

        self.tb_users = Table(
            "users",
            meta,
            Column("int_user_id", BigInteger, primary_key=True),
            Column("real_user_id", BigInteger),
            Column("name", Unicode),
            Column("discriminator", SmallInteger),
            Column("avatar", String, nullable=True),
            Column("is_deleted", Boolean),
            Column("is_bot", Boolean),
        )

    def __del__(self):
        self.conn.close()

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)

    # Specific queries
    def message_count(
        self, guild, user, *, included_channels=None, excluded_channels=None
    ):
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

        if included_channels is None and excluded_channels is None:
            raise TypeError("Both included_channels and excluded_channels are present")

        # Build WHERE filter
        conditions = [
            self.tb_messages.c.guild_id == guild.id,
            self.tb_messages.c.int_user_id == int_hash(user.id),
        ]

        channels = included_channels or excluded_channels
        if channels:
            condition = self.tb_channels.c.channel_id.in_(
                [channel.id for channel in channels]
            )

            if excluded_channels:
                condition = not_(condition)

            conditions.append(condition)

        sel = select(
            [
                func.count(self.tb_messages.c.message_id),
                func.count(self.tb_messages.c.edited_at),
                func.count(self.tb_messages.c.deleted_at),
            ]
        ).where(and_(*conditions))

        result = self.execute(sel)
        message_count, edited_count, deleted_count = result.fetchone()
        return message_count, edited_count, deleted_count

    def rollup_channel_usage(self, before_message_id=None, included_channels=()):
        message_id_fragment = ""

        if before_message_id is not None:
            message_id_fragment = "message_id < :before_message_id AND"

        stmt = text(
            f"""
            SELECT guild_id, channel_id, real_user_id, count
            FROM (
                SELECT guild_id, channel_id, int_user_id, COUNT(message_id) AS count
                FROM messages
                WHERE
                    {message_id_fragment}
                    channel_id IN :included_channels AND
                    deleted_at IS NULL
                GROUP BY guild_id, channel_id, int_user_id
            ) AS t
            JOIN users ON t.int_user_id=users.int_user_id;
        """
        )

        result = self.conn.execute(
            stmt,
            included_channels=included_channels,
            before_message_id=before_message_id,
        )

        return (row._asdict() for row in result)
