#
# cogs/navi/task/factory.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
A factory function to create appropriate Navi Task objects from
the values and attributes retrieved in the database.
"""

import logging
from collections import namedtuple

import discord

from futaba.enums import TaskType
from .change_roles import build_change_role_task
from .punish import build_punish_task
from .send_message import build_send_message_task

logger = logging.getLogger(__name__)

__all__ = ["build_navi_task"]

FakeUser = namedtuple("FakeUser", ("id", "name", "discriminator"))

TASK_BUILDERS = {
    TaskType.CHANGE_ROLES: build_change_role_task,
    TaskType.SEND_MESSAGE: build_send_message_task,
    TaskType.PUNISH: build_punish_task,
}


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
