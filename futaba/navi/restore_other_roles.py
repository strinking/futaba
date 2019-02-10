#
# cogs/navi/task/restore_other_roles.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging

import discord

from futaba.enums import TaskType
from futaba.utils import class_property
from .abc import AbstractNaviTask

logger = logging.getLogger(__name__)

__all__ = ["RestoreOtherRolesTask", "build_restore_other_roles_task"]


class RestoreOtherRolesTask(AbstractNaviTask):
    __slots__ = ("member", "reason")

    def __init__(self, bot, id, causer, timestamp, *, member, reason):
        super().__init__(bot, id, causer, timestamp, None)
        self.member = member
        self.reason = reason

    async def execute(self):
        logger.info("Restoring other roles to fulfill navi task %d", self.id)
        await self.bot.sql.moderation.restore_other_roles(self.member, self.reason)

    @class_property
    @classmethod
    def type(cls):
        return TaskType.RESTORE_OTHER_ROLES

    def build_parameters(self):
        return {"member_id": self.member.id, "reason": self.reason}


def build_restore_other_roles_task(bot, causer, guild, storage):
    # Parameters:
    # - member_id: int
    # - reason: str

    logger.debug("Creating RestoreOtherRoles with %s", storage.parameters)
    member_id = storage.parameters["member_id"]
    member = discord.utils.get(guild.members, id=member_id)
    if member is None:
        raise ValueError(f"Unable to find member with ID {member_id}")

    assert storage.recurrence is None, "Non-repeatable task has recurrence"
    return RestoreOtherRolesTask(
        bot,
        storage.id,
        causer,
        storage.timestamp,
        member=member,
        reason=storage.parameters["reason"],
    )
