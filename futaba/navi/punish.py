#
# cogs/navi/task/punish.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging

import discord

from futaba.enums import PunishAction, TaskType
from futaba.utils import class_property
from .abc import AbstractNaviTask

logger = logging.getLogger(__name__)

__all__ = ["PunishTask", "build_punish_task"]


class PunishTask(AbstractNaviTask):
    __slots__ = ("member", "action", "reason")

    def __init__(
        self, bot, id, causer, timestamp, recurrence, *, member, action, reason
    ):
        super().__init__(bot, id, causer, timestamp, recurrence)
        self.member = member
        self.action = action
        self.reason = reason

    async def execute(self):
        if self.action == PunishAction.APPLY_MUTE:
            logger.info(
                "Applying mute on '%s' (%d) to fulfill navi task %d",
                self.member.name,
                self.member.id,
                self.id,
            )
            await self.bot.punish.mute(self.guild, self.member, self.reason)
        elif self.action == PunishAction.APPLY_JAIL:
            logger.info(
                "Applying jail on '%s' (%d) to fulfill navi task %d",
                self.member.name,
                self.member.id,
                self.id,
            )
            await self.bot.punish.jail(self.guild, self.member, self.reason)
        elif self.action == PunishAction.RELIEVE_MUTE:
            logger.info(
                "Relieving mute on '%s' (%d) to fulfill navi task %d",
                self.member.name,
                self.member.id,
                self.id,
            )
            await self.bot.punish.unmute(self.guild, self.member, self.reason)
        elif self.action == PunishAction.RELIEVE_JAIL:
            logger.info(
                "Relieving jail on '%s' (%d) to fulfill navi task %d",
                self.member.name,
                self.member.id,
                self.id,
            )
            await self.bot.punish.unjail(self.guild, self.member, self.reason)
        elif self.action == PunishAction.RELIEVE_FOCUS:
            logger.info(
                "Relieving focus on '%s' (%d) to fulfill navi task %d",
                self.member.name,
                self.member.id,
                self.id,
            )
            await self.bot.punish.unfocus(self.guild, self.member, self.reason)

    @class_property
    @classmethod
    def type(cls):
        return TaskType.PUNISH

    def build_parameters(self):
        return {
            "member_id": self.member.id,
            "action": self.action.value,
            "reason": self.reason,
        }


def build_punish_task(bot, causer, guild, storage):
    # Parameters:
    # - member_id: int
    # - action: PunishAction
    # - reason: str

    member_id = storage.parameters["member_id"]
    member = discord.utils.get(guild.members, id=member_id)
    if member is None:
        raise ValueError(f"Unable to find member with ID {member_id}")

    return PunishTask(
        bot,
        storage.id,
        causer,
        storage.timestamp,
        storage.recurrence,
        member=member,
        action=PunishAction(storage.parameters["action"]),
        reason=storage.parameters["reason"],
    )
