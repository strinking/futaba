#
# converters/emoji.py
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
import unicodedata
from typing import Union

import discord
from discord.ext.commands import BadArgument, Converter

from futaba.unicode import normalize_caseless

from .utils import ID_REGEX

logger = logging.getLogger(__name__)

__all__ = ["EmojiConv"]

EMOJI_REGEX = re.compile(r"<:([A-Za-z0-9_\-]+(?:~[0-9]+)?):([0-9]+)>")


class EmojiConv(Converter):
    async def convert(self, ctx, argument) -> Union[discord.Emoji, str]:
        # Checking if it's not ASCII
        if not any(map(lambda c: ord(c) < 127, argument)):
            return argument

        # Search case-insensitively
        argument = normalize_caseless(argument)

        # Checking if it's an emoji id
        match = ID_REGEX.match(argument)
        if match is not None:
            emoji = ctx.bot.get_emoji(int(match[1]))
            if emoji is not None:
                return emoji

        # Checking if it's a unicode codepoint
        if argument.isdigit():
            try:
                return chr(int(argument))
            except (OverflowError, ValueError):
                pass

        # Checking if it's a discord emoji mention
        match = EMOJI_REGEX.match(argument)
        if match is not None:
            emoji = discord.utils.get(ctx.bot.emojis, id=int(match[2]))
            if emoji is not None:
                return emoji

        # Checking if it's the name of a discord emoji
        emoji = discord.utils.find(
            lambda e: argument == normalize_caseless(e.name), ctx.bot.emojis
        )
        if emoji is not None:
            return emoji

        # Checking if it's the name of a unicode emoji
        try:
            return unicodedata.lookup(argument)
        except KeyError:
            pass

        # No results!
        raise BadArgument(f'Unable to convert "{argument}" into an emoji')
