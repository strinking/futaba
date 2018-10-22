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

import asyncio
import logging
from abc import abstractmethod
from datetime import datetime

import discord

from futaba.utils import class_property

logger = logging.getLogger(__name__)

__all__ = ["TASK_COMPLETE", "AbstractNaviTask"]

TASK_COMPLETE = datetime(1, 1, 1)


class AbstractNaviTask:
    __slots__ = ("id", "causer", "timestamp", "recurrence", "async_task")

    def __init__(self, id, causer, timestamp, recurrence):
        self.id = id
        self.causer = causer
        self.timestamp = timestamp
        self.recurrence = recurrence
        self.async_task = None

    def due_next(self):
        now = datetime.now()
        if self.timestamp > now:
            return self.timestamp

        if self.recurrence is None:
            return TASK_COMPLETE
        else:
            remainder = (now - self.timestamp) % self.recurrence
            if remainder:
                remainder = self.recurrence - remainder
            return now + remainder

    def execute_later(self):
        """
        Puts this task on the asyncio event loop for later execution.
        Can only be done once.
        """

        if self.async_task is not None:
            raise ValueError(f"This task is already running: id {self.id}, {self!r}")

        self.async_task = asyncio.create_task(self.execute_future())

    async def execute_future(self):
        """
        The blocking coroutine that will run this task to completion. If it is a recurring
        task, it will run it in perpetuity.
        """

        logger.info("Starting full future execution of task %d", self.id)
        due_next = self.due_next()
        if due_next is TASK_COMPLETE:
            return

        duration = (datetime.now() - due_next).total_seconds()
        await asyncio.sleep(duration)
        await self.execute()

        if self.recurrence is not None:
            logger.debug(
                "Ran for the first time, task %d now looping continually...", self.id
            )
            duration = self.recurrence.total_seconds()
            while True:
                await asyncio.sleep(duration)
                await self.execute()

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
        """
        Abstract method to be overloaded by child classes. This is the method that
        does whatever this task is supposed to do.
        """

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
