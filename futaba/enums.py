#
# enums.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from enum import Enum, unique

import discord

__all__ = [
    'FilterType',
    'LocationType',
]

@unique
class FilterType(Enum):
    FLAG = 'flag'
    BLOCK = 'block'
    JAIL = 'jail'

    @property
    def emoji(self):
        if self == FilterType.FLAG:
            return '\N{WARNING SIGN}'
        elif self == FilterType.BLOCK:
            return '\N{NO ENTRY SIGN}'
        elif self == FilterType.JAIL:
            return '\N{POLICE CARS REVOLVING LIGHT}'
        else:
            raise ValueError(f"Invalid enum value: {self!r}")

    @property
    def description(self):
        if self == FilterType.FLAG:
            return 'Flagged words'
        elif self == FilterType.BLOCK:
            return 'Denied words'
        elif self == FilterType.JAIL:
            return 'Auto-jail words'
        else:
            raise ValueError(f"Invalid enum value: {self!r}")

@unique
class LocationType(Enum):
    CHANNEL = 'channel'
    GUILD = 'guild'

    @staticmethod
    def of(location):
        if isinstance(location, discord.Guild):
            return LocationType.GUILD
        elif isinstance(location, discord.TextChannel):
            return LocationType.CHANNEL
        else:
            return TypeError(f"No location type for {location!r}")
