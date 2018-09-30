#
# converters/user.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
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

from .utils import ID_REGEX

logger = logging.getLogger(__name__)

__all__ = [
    'MemberConv',
    'UserConv',
]

MENTION_REGEX = re.compile(r'<@!?([0-9]{15,21})>$')
USERNAME_DISCRIM_REGEX = re.compile(r'(.+)#([0-9]{4})')

async def get_user(bot, argument, user_list):
    argument = normalize_caseless(argument)

    logger.debug("Checking if it's a user ID or mention")
    match = ID_REGEX.match(argument) or MENTION_REGEX.match(argument)
    if match is not None:
        user = await bot.get_user_info(int(match[1]))
        if user is not None:
            return user

    logger.debug("Checking if it's in the form username#discriminator")
    match = USERNAME_DISCRIM_REGEX.match(argument)
    if match is not None:
        name, discrim = normalize_caseless(match[1]), int(match[2])
        def check(user):
            uname = normalize_caseless(user.name)
            udiscrim = user.discriminator
            return name == uname and discrim == udiscrim
        user = discord.utils.find(check, user_list)
        if user is not None:
            return user

    logger.debug("Checking if it's a username")
    user = discord.utils.find(lambda u: name == normalize_caseless(u.name), user_list)
    if user is not None:
        return user

    logger.debug("Checking if it's a nickname")
    def check_user(user):
        nick = getattr(user, 'nick', None)
        if nick is None:
            return False
        return name == normalize_caseless(nick)

    user = discord.utils.find(check_user, user_list)
    if user is not None:
        return user

    logger.debug("No results found")
    return BadArgument(f'Unable to find user with description "{argument}"')

class UserConv(Converter):
    async def convert(self, ctx, argument) -> discord.User:
        return await get_user(ctx.bot, argument, ctx.bot.users)

class MemberConv(Converter):
    async def convert(self, ctx, argument) -> discord.Member:
        user = await get_user(ctx.bot, argument, ctx.guild.members)
        if not isinstance(user, discord.Member):
            raise BadArgument(f'Found user that matched "{argument}", but they were not a member')
        return user
