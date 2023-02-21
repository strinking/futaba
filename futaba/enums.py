#
# enums.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from enum import Enum, unique

import dateparser
import discord


@unique
class Reactions(Enum):
    SUCCESS = "\N{WHITE HEAVY CHECK MARK}"
    WARNING = "\N{WARNING SIGN}"
    FAIL = "\N{CROSS MARK}"
    DENY = "\N{NO ENTRY SIGN}"
    MISSING = "\N{BLACK QUESTION MARK ORNAMENT}"
    WAITING = "\N{HOURGLASS}"
    NETWORK = "\N{ELECTRIC PLUG}"
    HELP = "\N{BOOKS}"

    async def add(self, message: discord.Message):
        try:
            await message.add_reaction(self.value)
        except discord.NotFound:
            # Message was deleted
            pass


@unique
class JoinAlertKey(Enum):
    CREATION = "created_at"  # datetime
    ID = "id"  # int
    NAME = "name"  # str
    DISCRIM = "discriminator"  # str
    AVATAR = "avatar"  # Optional[str]
    STATUS = "status"  # discord.Status

    @classmethod
    def parse(cls, arg):
        if arg in ("created", "creation", "created at", "created_at"):
            return cls.CREATION
        elif arg in ("id", "user id", "member id", "user_id"):
            return cls.ID
        elif arg in ("name", "username"):
            return cls.NAME
        elif arg in ("discrim", "discriminator"):
            return cls.DISCRIM
        elif arg in ("avatar", "avatar hash"):
            return cls.AVATAR
        elif arg in ("status", "user status"):
            return cls.STATUS
        else:
            raise ValueError(f"No JoinAlertKey for value: {arg}")

    def parse_value(self, arg):
        if self == JoinAlertKey.CREATION:
            date = dateparser.parse(arg)
            if date is None:
                raise ValueError(f"Unknown date/time: {arg}")
            return date
        elif self == JoinAlertKey.ID:
            try:
                id = int(arg)
                if id < 0 or id > 2**63 - 1:
                    raise ValueError()
            except ValueError:
                # Raise with different message
                raise ValueError(f"Invalid discord ID: {arg}")
            else:
                return id
        elif self == JoinAlertKey.NAME:
            return arg
        elif self == JoinAlertKey.DISCRIM:
            try:
                discrim = int(arg)
                if discrim <= 1 or discrim > 9999:
                    raise ValueError()
            except ValueError:
                # Raise with different message
                raise ValueError(f"Invalid discriminator: {arg}")
            else:
                return f"{discrim:04}"
        elif self == JoinAlertKey.AVATAR:
            return arg or None
        elif self == JoinAlertKey.STATUS:
            try:
                return discord.Status(arg.lower())
            except ValueError:
                # Raise with different message
                raise ValueError(f"Invalid discord status: {arg}")
        else:
            raise ValueError("Not an enum instance of JoinAlertKey")

    @property
    def display_name(self):
        if self == JoinAlertKey.CREATION:
            return "account creation date"
        elif self == JoinAlertKey.ID:
            return "user id"
        elif self == JoinAlertKey.NAME:
            return "username"
        elif self == JoinAlertKey.DISCRIM:
            return "discriminator"
        elif self == JoinAlertKey.AVATAR:
            return "avatar hash"
        elif self == JoinAlertKey.STATUS:
            return "status"
        else:
            raise ValueError("Not an enum instance of JoinAlertKey")


@unique
class ValueRelationship(Enum):
    LESS_THAN = "<"
    GREATER_THAN = ">"
    LESS_OR_EQUAL = "<="
    GREATER_OR_EQUAL = ">="
    EQUAL_TO = "="
    NOT_EQUAL = "!="
    CONTAINS = "~"

    @property
    def comparator(self):
        return VALUE_RELATIONSHIP_COMPARATORS[self]

    @property
    def symbol(self):
        return VALUE_RELATIONSHIP_SYMBOLS[self]


VALUE_RELATIONSHIP_COMPARATORS = {
    ValueRelationship.LESS_THAN: lambda x, y: x < y,
    ValueRelationship.LESS_OR_EQUAL: lambda x, y: x <= y,
    ValueRelationship.GREATER_THAN: lambda x, y: x > y,
    ValueRelationship.GREATER_OR_EQUAL: lambda x, y: x >= y,
    ValueRelationship.EQUAL_TO: lambda x, y: x == y,
    ValueRelationship.NOT_EQUAL: lambda x, y: x != y,
    ValueRelationship.CONTAINS: lambda x, y: y in x,
}

VALUE_RELATIONSHIP_SYMBOLS = {
    ValueRelationship.LESS_THAN: "<",
    ValueRelationship.LESS_OR_EQUAL: "\N{LESS-THAN OR EQUAL TO}",
    ValueRelationship.GREATER_THAN: ">",
    ValueRelationship.GREATER_OR_EQUAL: "\N{GREATER-THAN OR EQUAL TO}",
    ValueRelationship.EQUAL_TO: "=",
    ValueRelationship.NOT_EQUAL: "\N{NOT EQUAL TO}",
    ValueRelationship.CONTAINS: "\N{ALMOST EQUAL TO}",
}


@unique
class MemberLeaveType(Enum):
    LEFT = "member_left"
    PRUNED = "pruned"
    KICKED = "kicked"
    BANNED = "banned"


@unique
class NameType(Enum):
    USER = "username"
    NICK = "nickname"


@unique
class FilterType(Enum):
    FLAG = "flag"
    BLOCK = "block"
    JAIL = "jail"

    @property
    def level(self):
        if self == FilterType.FLAG:
            return 1
        elif self == FilterType.BLOCK:
            return 2
        elif self == FilterType.JAIL:
            return 3
        else:
            raise ValueError(f"Invalid enum value: {self!r}")

    @property
    def emoji(self):
        if self == FilterType.FLAG:
            return "\N{WARNING SIGN}"
        elif self == FilterType.BLOCK:
            return "\N{NO ENTRY SIGN}"
        elif self == FilterType.JAIL:
            return "\N{POLICE OFFICER}"
        else:
            raise ValueError(f"Invalid enum value: {self!r}")

    @property
    def description(self):
        if self == FilterType.FLAG:
            return "Flagged"
        elif self == FilterType.BLOCK:
            return "Blocked"
        elif self == FilterType.JAIL:
            return "Auto-jail"
        else:
            raise ValueError(f"Invalid enum value: {self!r}")


@unique
class LocationType(Enum):
    GUILD = "guild"
    CHANNEL = "channel"
    USER = "user"

    @staticmethod
    def of(location):
        if isinstance(location, discord.Guild):
            return LocationType.GUILD
        elif isinstance(location, discord.TextChannel):
            return LocationType.CHANNEL
        elif isinstance(location, discord.abc.User):
            return LocationType.USER
        else:
            raise TypeError(f"No location type for {location!r}")


@unique
class TaskType(Enum):
    CHANGE_ROLES = "change_roles"
    SEND_MESSAGE = "send_message"
    PUNISH = "punish"


@unique
class PunishAction(Enum):
    APPLY_MUTE = "apply_mute"
    APPLY_JAIL = "apply_jail"
    RELIEVE_MUTE = "relieve_mute"
    RELIEVE_JAIL = "relieve_jail"
    RELIEVE_FOCUS = "relieve_focus"


@unique
class ManualModActionType(Enum):
    SPECIAL_ROLE_MEMBER = "member"
    SPECIAL_ROLE_GUEST = "guest"
    SPECIAL_ROLE_MUTE = "mute"
    SPECIAL_ROLE_JAIL = "jail"
    SPECIAL_ROLE_FOCUS = "focus"
    KICK_MEMBER = "kick"
    BAN_MEMBER = "ban"
