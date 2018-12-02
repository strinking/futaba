#
# infraction.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from futaba.enums import InfractionType


class Infraction:
    __slots__ = ("id", "timestamp", "guild", "user", "causer", "type")

    def __init__(self, *, id, timestamp, guild, user, causer, type):
        self.id = id
        self.timestamp = timestamp
        self.guild = guild
        self.user = user
        self.causer = causer
        self.type = type

    @classmethod
    def build(cls, *, id, timestamp, guild, user, causer, type, attributes):
        if type == InfractionType.NOTE:
            return NoteInfraction(
                id=id,
                timestamp=timestamp,
                guild=guild,
                user=user,
                causer=causer,
                type=type,
                note=attributes["note"],
            )
        elif type == InfractionType.WARNING:
            return WarningInfraction(
                id=id,
                timestamp=timestamp,
                guild=guild,
                user=user,
                causer=causer,
                type=type,
                note=attributes["note"],
                expiration=attributes["expiration"],
            )
        else:
            return cls(
                id=id,
                timestamp=timestamp,
                guild=guild,
                user=user,
                causer=causer,
                type=type,
            )


class NoteInfraction:
    __slots__ = ("note",)

    def __init__(self, *, id, timestamp, guild, user, causer, type, note):
        super().__init__(
            id=id, timestamp=timestamp, guild=guild, user=user, causer=causer, type=type
        )
        self.note = note


class WarningInfraction:
    __slots__ = ("note", "expiration")

    def __init__(self, *, id, timestamp, guild, user, causer, type, note, expiration):
        super().__init__(
            id=id, timestamp=timestamp, guild=guild, user=user, causer=causer, type=type
        )
        self.note = note
        self.expiration = expiration
