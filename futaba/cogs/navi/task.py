#
# cogs/navi/task.py
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
Module that has singular or recurring Navi task objects which will
be executed by Futaba in the future.
"""

import asyncio
import logging
from abc import abstractmethod
from collections import namedtuple
from datetime import datetime

import discord
from futaba.enums import TaskType
from futaba.utils import class_property

logger = logging.getLogger(__name__)

__all__ = [
    "TASK_COMPLETE",
    "AbstractNaviTask",
    "ChangeRolesNaviTask",
    "navi_task_factory",
]

TASK_COMPLETE = datetime(1, 1, 1)

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


class ChangeRolesNaviTask(AbstractNaviTask):
    __slots__ = ("member", "to_add", "to_remove", "reason")

    def __init__(
        self, id, causer, timestamp, recurrence, member, to_add, to_remove, reason
    ):
        super().__init__(id, causer, timestamp, recurrence)
        self.member = member
        self.to_add = to_add
        self.to_remove = to_remove
        self.reason = reason

    async def execute(self):
        logger.info("Adding/removing roles in navi task %d", self.id)
        await asyncio.gather(
            self.member.add_roles(*self.to_add, reason=self.reason, atomic=True),
            self.member.remove_roles(*self.to_remove, reason=self.reason, atomic=True),
        )

    @class_property
    @classmethod
    def type(cls):
        return TaskType.CHANGE_ROLES

    def build_parameters(self):
        return {
            "member_id": self.member.id,
            "add_role_ints": [role.id for role in self.to_add],
            "remove_role_ints": [role.id for role in self.to_remove],
            "reason": self.reason,
        }


def build_role_task(bot, causer, guild, storage):
    # Parameters:
    # - member_id: int
    # - add_role_ids: [int]
    # - remove_role_ids: [int]
    # - reason: str

    logger.debug("Creating ChangeRolesNaviTask with %s", storage.parameters)
    member_id = storage.parameters["member_id"]
    member = discord.utils.get(guild.member, id=member_id)
    if member is None:
        raise ValueError(f"Unable to find member with ID {member_id}")

    to_add = []
    for role_id in storage.parameters["add_role_ids"]:
        role = discord.utils.get(guild.roles, id=role_id)
        if role is None:
            logger.info("Couldn't find role to add with ID of %d", role_id)
        else:
            to_add.append(role)

    to_remove = []
    for role_id in storage.parameters["remove_role_ids"]:
        role = discord.utils.get(guild.roles, id=role_id)
        if role is None:
            logger.info("Couldn't find role to remove with ID of %d", role_id)
        else:
            to_remove.append(role)

    return ChangeRolesNaviTask(
        storage.id,
        causer,
        storage.timestamp,
        storage.recurrence,
        member,
        to_add,
        to_remove,
        storage.parameters["reason"],
    )


TASK_BUILDERS = {TaskType.CHANGE_ROLES: build_role_task}


def navi_task_factory(bot, storage):
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
