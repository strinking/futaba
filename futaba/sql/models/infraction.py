#
# sql/models/infraction.py
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
Has the model for infractions and other records about members.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from datetime import datetime

from sqlalchemy import and_, desc
from sqlalchemy import BigInteger, Column, DateTime, Enum, Integer, JSON, Table
from sqlalchemy import ForeignKey, Sequence, UniqueConstraint
from sqlalchemy.sql import select

from futaba.enums import InfractionType
from futaba.infraction import Infraction
from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["InfractionModel"]


class InfractionModel:
    __slots__ = ("sql", "tb_infractions")

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_infractions = Table(
            "infractions",
            meta,
            Column(
                "infraction_id",
                Integer,
                Sequence("infraction_seq", metadata=meta),
                primary_key=True,
            ),
            Column("timestamp", DateTime),
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id")),
            Column("user_id", BigInteger),
            Column("causer_id", BigInteger),
            Column("type", Enum(InfractionType)),
            Column("attributes", JSON),
            UniqueConstraint("timestamp", "guild_id", "user_id", name="infraction_uq"),
        )

        register_hook("on_guild_leave", self.remove_all_infractions)

    def get_infractions(self, member, count=15):
        logger.info(
            "Getting infractions for member '%s' (%d) in guild '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )
        sel = (
            select(
                [
                    self.tb_infractions.c.infraction_id,
                    self.tb_infractions.c.timestamp,
                    self.tb_infractions.c.causer_id,
                    self.tb_infractions.c.type,
                    self.tb_infractions.c.attributes,
                ]
            )
            .where(
                and_(
                    self.tb_infractions.c.guild_id == member.guild.id,
                    self.tb_infractions.c.user_id == member.id,
                )
            )
            .order_by(desc(self.tb_infractions.c.timestamp))
            .limit(count)
        )
        result = self.sql.execute(sel)

        infractions = []
        for id, timestamp, causer_id, type, attrs in result.fetchall():
            causer = member.guild.get_member(causer_id)
            infractions.append(
                Infraction.build(
                    id=id,
                    timestamp=timestamp,
                    guild=member.guild,
                    user=member,
                    causer=causer,
                    type=type,
                    attributes=attrs,
                )
            )

    def add_infraction(self, causer, member, type, attributes=None):
        logger.info(
            "Adding infraction for member '%s' (%d) in guild '%s' (%d) caused by '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
            causer.name,
            causer.id,
        )

        timestamp = datetime.utcnow()
        ins = self.tb_infractions.insert().values(
            timestamp=timestamp,
            guild_id=member.guild.id,
            user_id=member.id,
            causer_id=causer.id,
            type=type,
            attributes=attributes or {},
        )
        result = self.sql.execute(ins)

        id, = result.inserted_primary_key
        return Infraction.build(
            id=id,
            timestamp=timestamp,
            guild=member.guild,
            user=member,
            causer=causer,
            type=type,
            attributes=attributes,
        )

    def add_member_note(self, causer, member, note):
        logger.debug("Adding note on member")
        return self.add_infraction(causer, member, InfractionType.NOTE, {"note": note})

    def add_member_warning(self, causer, member, note, expiration):
        logger.debug("Adding warning for member")
        return self.add_infraction(
            causer,
            member,
            InfractionType.WARNING,
            {"note": note, "expiration": expiration},
        )

    def remove_infraction(self, id):
        logger.info("Expunging infraction with ID %d", id)
        delet = self.tb_infractions.delete().where(
            self.tb_infractions.c.infraction_id == id
        )
        self.sql.execute(delet)

    def remove_all_infractions(self, guild):
        logger.info("Removing all infractions in guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_infractions.delete().where(
            self.tb_infractions.c.guild_id == guild.id
        )
        self.sql.execute(delet)
