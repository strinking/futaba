#
# cogs/navi/task/abc.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

""" Abstract class for Navi tasks. """

import logging
from abc import abstractmethod
from datetime import datetime

import discord

from futaba.utils import class_property

logger = logging.getLogger(__name__)

__all__ = [
    "TASK_COMPLETE",
    "AbstractNaviTask",
]

TASK_COMPLETE = datetime(1, 1, 1)


class AbstractNaviTask:
    __slots__ = ("id", "causer", "timestamp", "recurrence")

    def __init__(self, id, causer, timestamp, recurrence):
        self.id = id
        self.causer = causer
        self.timestamp = timestamp
        self.recurrence = recurrence

    def due_next(self):
        now = datetime.utcnow()
        if self.timestamp > now:
            return self.timestamp

        if self.recurrence is None:
            return TASK_COMPLETE
        else:
            remainder = (now - self.timestamp) % self.recurrence
            if remainder:
                remainder = self.recurrence - remainder
            return now + remainder

    @property
    def guild_id(self):
        if isinstance(self.causer, discord.Member):
            return self.causer.guild.id

        return None

    @class_property
    @classmethod
    @abstractmethod
    def type(cls):
        pass

    @abstractmethod
    async def execute(self):
        pass

    @abstractmethod
    def build_parameters(self):
        pass

    def __lt__(self, other):
        if not isinstance(other, AbstractNaviTask):
            raise TypeError(
                f"Cannot compare instance of {type(self)!r} and {type(other)!r}"
            )

        return self.due_next() < other.due_next()
