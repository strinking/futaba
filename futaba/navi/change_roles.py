#
# cogs/navi/task/change_roles.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging

import discord

from futaba.enums import TaskType
from futaba.utils import class_property
from .abc import AbstractNaviTask

logger = logging.getLogger(__name__)

__all__ = ["ChangeRolesTask", "build_change_role_task"]


class ChangeRolesTask(AbstractNaviTask):
    __slots__ = ("member", "to_add", "to_remove", "reason")

    def __init__(
        self,
        bot,
        id,
        causer,
        timestamp,
        recurrence,
        *,
        member,
        reason,
        to_add=None,
        to_remove=None,
    ):
        super().__init__(bot, id, causer, timestamp, recurrence)
        self.member = member
        self.to_add = to_add if to_add is not None else []
        self.to_remove = to_remove if to_remove is not None else []
        self.reason = reason

    async def execute(self):
        logger.info("Adding/removing roles to fulfill navi task %d", self.id)
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
            "add_role_ids": [role.id for role in self.to_add],
            "remove_role_ids": [role.id for role in self.to_remove],
            "reason": self.reason,
        }


def build_change_role_task(bot, causer, guild, storage):
    # Parameters:
    # - member_id: int
    # - add_role_ids: List[int]
    # - remove_role_ids: List[int]
    # - reason: str

    member_id = storage.parameters["member_id"]
    member = discord.utils.get(guild.members, id=member_id)
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

    return ChangeRolesTask(
        bot,
        storage.id,
        causer,
        storage.timestamp,
        storage.recurrence,
        member=member,
        to_add=to_add,
        to_remove=to_remove,
        reason=storage.parameters["reason"],
    )
