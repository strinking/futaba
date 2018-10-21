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
from collections import namedtuple
from datetime import datetime

import discord

from futaba.enums import TaskType
from futaba.utils import class_property
from .change_roles import build_change_role_task
from .send_message import build_send_message_task

logger = logging.getLogger(__name__)

__all__ = [
    "TASK_COMPLETE",
    "AbstractNaviTask",
    "build_navi_task",
]

TASK_COMPLETE = datetime(1, 1, 1)
TASK_BUILDERS = {
    TaskType.CHANGE_ROLES: build_change_role_task,
    TaskType.SEND_MESSAGE: build_send_message_task,
}

FakeUser = namedtuple("FakeUser", ("id", "name", "discriminator"))


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


def build_navi_task(bot, storage):
    logger.debug("Creating NaviTask for %r", storage)
    causer = discord.utils.get(bot.users, id=storage.user_id)
    if causer is None:
        logger.debug(
            "Couldn't find causing user %d, returning dummy user", storage.user_id
        )
        causer = FakeUser(
            id=storage.user_id, name=int(storage.user_id), discriminator="0000"
        )

    guild = discord.utils.get(bot.guilds, id=storage.guild_id)
    if guild is None:
        raise ValueError(f"Unable to find guild with ID {storage.guild_id}")

    return TASK_BUILDERS[storage.task_type](bot, causer, guild, storage)
