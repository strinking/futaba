#
# converters/user.py
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
from itertools import chain, islice
from typing import Iterable

import textdistance
import discord
from discord.ext.commands import BadArgument, Converter

from futaba.unicode import normalize_caseless

from .utils import ID_REGEX

logger = logging.getLogger(__name__)

__all__ = ["similar_text", "similar_users", "MemberConv", "UserConv"]

MENTION_REGEX = re.compile(r"<@!?([0-9]{15,21})>$")
USERNAME_DISCRIM_REGEX = re.compile(r"@?(.+)#([0-9]{4})")


def similar_text(word1, word2) -> float:
    """
    Determines if the two strings are similar enough given the passed threshold.
    An alias for textdistance.overlap.similarity().
    """

    return textdistance.overlap.similarity(word1, word2)


async def similar_users(bot, argument, max_entries=10) -> Iterable[discord.User]:
    """
    Gets a list of user IDs that are similar to the argument.
    They are ranked in order of similarity.
    """

    # Get exact matches, if any
    try:
        user = await get_user(bot, argument, bot.users)
        matching = [user]
    except BadArgument:
        matching = []

    # Search case-insensitively
    argument = normalize_caseless(argument)

    # Do a fuzzy text search among users
    users = []
    for user in bot.users:
        similar = similar_text(argument, normalize_caseless(user.name))
        if getattr(user, "nick", None) is not None:
            similar = max(
                similar, similar_text(argument, normalize_caseless(user.nick))
            )
        if user not in matching:
            users.append((user, similar))

    # Sort by similarity
    users.sort(key=lambda p: p[1], reverse=True)
    matching.extend(user for user, similar in users if similar > 0.3)

    # Done
    return islice(matching, 0, max_entries)


async def get_user(bot, argument, user_list):
    argument = normalize_caseless(argument)

    # Checking if it's a user id or mention
    match = ID_REGEX.match(argument) or MENTION_REGEX.match(argument)
    if match is not None:
        id = int(match[1])
        user = bot.get_user(id)
        if user is not None:
            return user

        try:
            return await bot.fetch_user(id)
        except discord.NotFound:
            pass

    # Checking if it's a user#discrim
    match = USERNAME_DISCRIM_REGEX.match(argument)
    if match is not None:
        name, discrim = normalize_caseless(match[1]), match[2]

        def user_discrim_check(user):
            uname = normalize_caseless(user.name)
            udiscrim = user.discriminator
            return name == uname and discrim == udiscrim

        user = discord.utils.find(user_discrim_check, user_list)
        if user is not None:
            return user
        del name, discrim

    # Checking if it's a username or nickname
    def name_check(user):
        if argument == normalize_caseless(user.name):
            return True

        nick = getattr(user, "nick", None)
        if nick is not None:
            if argument == normalize_caseless(nick):
                return True

        return False

    user = discord.utils.find(name_check, user_list)
    if user is not None:
        return user

    # No results!
    raise BadArgument(f'Unable to find user with description "{argument}"')


def get_member_if_exists(guild, user):
    if guild is not None:
        if not isinstance(user, discord.Member):
            member = discord.utils.get(guild.members, id=user.id)
            if member is not None:
                return member
    return user


class UserConv(Converter):
    async def convert(self, ctx, argument) -> discord.User:
        user_list = tuple(chain(ctx.guild.members, ctx.bot.users))
        user = await get_user(ctx.bot, argument, user_list)
        user = get_member_if_exists(ctx.guild, user)
        return user


class MemberConv(Converter):
    async def convert(self, ctx, argument) -> discord.Member:
        user = await get_user(ctx.bot, argument, ctx.guild.members)
        user = get_member_if_exists(ctx.guild, user)
        if not isinstance(user, discord.Member):
            raise BadArgument(
                f'Found user that matched "{argument}", but they were not a member'
            )
        return user
