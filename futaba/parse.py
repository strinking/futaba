#
# discord.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging
import re

import discord

from futaba.utils import normalize_caseless

logger = logging.getLogger(__name__)

__all__ = [
    'channel_mention',
    'user_mention',
    'role_mention',
    'name_discrim_search',
    'get_user_id',
]

CHANNEL_MENTION_REGEX = re.compile(r'<#([0-9]+)>')
USER_MENTION_REGEX = re.compile(r'<@([0-9]+)>')
ROLE_MENTION_REGEX = re.compile(r'<@&([0-9]+)>')
USERNAME_DISCRIM_REGEX = re.compile(r'(.+)#([0-9]{4})')

def channel_mention(mention):
    '''
    Parses a channel mention, returning the ID inside.
    The id might not correspond with an actual channel.
    '''

    logger.debug("Checking possible channel mention '%s'", mention)

    match = CHANNEL_MENTION_REGEX.match(mention)
    if match is None:
        return None

    return int(match[1])

def user_mention(mention):
    '''
    Parses a user mention, returning the ID inside.
    The id might not correspond with an actual user.
    '''

    logger.debug("Checking possible user mention '%s'", mention)

    match = USER_MENTION_REGEX.match(mention)
    if match is None:
        return None

    return int(match[1])

def role_mention(mention):
    '''
    Parses the role mention, returning the ID insice.
    The id might not correspond with an actual role.
    Does not work on @everyone or @here pings.
    '''

    logger.debug("Checking possible role mention '%s'", mention)

    match = ROLE_MENTION_REGEX.match(mention)
    if match is None:
        return None

    return int(match[1])

def name_discrim_search(s, users=(), ignorecase=False):
    match = USERNAME_DISCRIM_REGEX.match(s)
    if match is None:
        return None

    name, discrim = match[1], int(match[2])
    if ignorecase:
        name = normalize_caseless(name)
        return discord.utils.find(lambda u: name == normalize_caseless(u.name) and discrim == u.discriminator)
    else:
        return discord.utils.get(users, name=name, discriminator=discrim)

def get_user_id(name, users=()):
    # Allow case-insensitive searching
    name = normalize_caseless(name)

    # Check for user ID
    logger.debug("get_user_id: checking if it's an integer")
    if name.isdigit():
        return int(name)

    # Check for mention
    logger.debug("get_user_id: checking if it's a user mention")
    id = user_mention(name)
    if id is not None:
        return id

    # Check by name#discrim
    logger.debug("get_user_id: checking if it's a username#discriminator")
    user = name_discrim_search(name, users, True)
    if user is not None:
        return user.id

    # Check by username
    logger.debug("get_user_id: checking if it's a username")
    user = discord.utils.get(users, name=name)
    if user is not None:
        return user.id

    # Check by nickname
    def check_user(user):
        nick = getattr(user, 'nick', None)
        if nick is None:
            return False

        return name == normalize_caseless(nick)

    logger.debug("get_user_id: checking if it's a nickname")
    user = discord.utils.find(check_user, users)
    if user is not None:
        return user.id

    # No results
    logger.debug("get_user_id found no results!")
    return None
