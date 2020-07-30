#
# converters/channel.py
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
import re

import discord
from discord.ext.commands import BadArgument, Converter

from futaba.unicode import normalize_caseless

from .utils import DUAL_ID_REGEX, ID_REGEX

logger = logging.getLogger(__name__)

__all__ = ["TextChannelConv", "GuildChannelConv"]

CHANNEL_MENTION_REGEX = re.compile(r"<#([0-9]+)>")


async def get_channel(bot, argument):
    argument = normalize_caseless(argument)

    # Checking if it's a dual ID
    match = DUAL_ID_REGEX.match(argument)
    if match is not None:
        chan = bot.get_channel(int(match[1]))
        if chan is not None:
            return chan

    # Checking if it's a channel id
    match = ID_REGEX.match(argument)
    if match is not None:
        chan = bot.get_channel(int(match[1]))
        if chan is not None:
            return chan

    # Checking if it's a channel mention
    match = CHANNEL_MENTION_REGEX.match(argument)
    if match is not None:
        chan = bot.get_channel(int(match[1]))
        if chan is not None:
            return chan

    # Checking if it's a channel name
    for chan in bot.get_all_channels():
        if argument == normalize_caseless(chan.name):
            return chan

    # No results!
    raise BadArgument(f'Unable to find channel with description "{argument}"')


class TextChannelConv(Converter):
    async def convert(self, ctx, argument) -> discord.TextChannel:
        chan = await get_channel(ctx.bot, argument)
        if not isinstance(chan, discord.TextChannel):
            raise BadArgument(
                f'Found channel that matched "{argument}", but was not a text channel'
            )
        return chan


class GuildChannelConv(Converter):
    async def convert(self, ctx, argument) -> discord.abc.GuildChannel:
        chan = await get_channel(ctx.bot, argument)
        if not isinstance(chan, discord.abc.GuildChannel):
            raise BadArgument(
                f'Found channel that matched "{argument}", but was not a guild channel'
            )
        return chan
