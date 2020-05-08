#
# converters/message.py
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
import re

import discord
from discord.ext.commands import BadArgument, Converter

from futaba.utils import first

from .utils import DUAL_ID_REGEX, ID_REGEX

logger = logging.getLogger(__name__)

__all__ = ["MessageConv"]

JUMP_LINK_REGEX = re.compile(
    r"https://discordapp.com/channels/([0-9]+)/([0-9]+)/([0-9]+)", re.IGNORECASE
)


class MessageConv(Converter):
    @staticmethod
    def get_channels_and_id(ctx, argument):
        # Checking if it's a dual ID
        match = DUAL_ID_REGEX.match(argument)
        if match is not None:
            channel_id = int(match[1])
            message_id = int(match[2])

            channel = ctx.guild.get_channel(channel_id)
            if channel is None:
                return BadArgument(f"No channel found in guild with ID {channel_id}")

            return [channel], message_id

        # Checking if it's an id
        match = ID_REGEX.match(argument)
        if match is not None:
            return ctx.guild.text_channels, int(match[1])

        # Checking if it's a jump link
        match = JUMP_LINK_REGEX.match(argument)
        if match is not None:
            guild_id = int(match[1])
            channel_id = int(match[2])
            message_id = int(match[3])

            if guild_id == ctx.guild.id:
                guild = ctx.guild
            else:
                guild = ctx.bot.get_guild(guild_id)
                if guild is None:
                    raise BadArgument(f"Not in any guild with ID {guild_id}")

            channel = guild.get_channel(channel_id)
            if channel is None:
                raise BadArgument(f"No channel found in guild with ID {channel_id}")

            return [channel], message_id

        # No results!
        raise BadArgument(f"Unable to find message with description '{argument}'")

    @staticmethod
    async def find_in_channel(channel, id):
        try:
            return await channel.fetch_message(id)
        except discord.NotFound:
            return None

    async def convert(self, ctx, argument) -> discord.Message:
        if ctx.guild is None:
            raise BadArgument("Refusing to find message because we are not in a guild")

        channels, id = self.get_channels_and_id(ctx, argument)
        results = await asyncio.gather(
            *[self.find_in_channel(channel, id) for channel in channels]
        )

        message = first(results)
        if message is None:
            raise BadArgument(f"No message found with ID {id}")

        return message
