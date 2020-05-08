#
# cogs/navi/task/send_message.py
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

from futaba.enums import LocationType, TaskType
from futaba.utils import class_property, DictEmbed
from .abc import AbstractNaviTask

logger = logging.getLogger(__name__)

__all__ = ["SendMessageTask", "build_send_message_task"]


class SendMessageTask(AbstractNaviTask):
    __slots__ = ("output", "content", "embed", "metadata")

    def __init__(
        self,
        bot,
        id,
        causer,
        timestamp,
        recurrence,
        output,
        *,
        content=None,
        embed=None,
        metadata=None,
    ):
        super().__init__(bot, id, causer, timestamp, recurrence)
        self.output = output
        self.content = content
        self.embed = embed if isinstance(embed, discord.Embed) else DictEmbed(embed)
        self.metadata = metadata

    async def execute(self):
        logger.info("Sending message to fulfill navi task %d", self.id)
        await self.output.send(content=self.content, embed=self.embed)

    @class_property
    @classmethod
    def type(cls):
        return TaskType.SEND_MESSAGE

    def build_parameters(self):
        return {
            "location_id": self.output.id,
            "location_type": LocationType.of(self.output).value,
            "content": self.content,
            "embed": self.embed.to_dict(),
            "metadata": self.metadata,
        }


def build_send_message_task(bot, causer, guild, storage):
    # Parameters:
    # - location_id: int
    # - location_type: str
    # - content: Optional[str]
    # - embed: Optional[dict]

    location_id = storage.parameters["location_id"]
    location_type = storage.parameters["location_type"]
    if location_type == LocationType.CHANNEL:
        output = discord.utils.get(guild.text_channels, id=location_id)
        if output is None:
            raise ValueError(f"Could not find channel with ID {location_id}")
    elif location_type == LocationType.USER:
        output = causer
    else:
        raise ValueError(
            f"Invalid location type for send message task: {location_type}"
        )

    return SendMessageTask(
        bot,
        storage.id,
        causer,
        storage.timestamp,
        storage.recurrence,
        output,
        content=storage.parameters["content"],
        embed=storage.parameters["embed"],
    )
