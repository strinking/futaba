#
# discord.py
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
import unicodedata
from itertools import islice
from typing import Iterable, Optional, Union

import discord
import textdistance

from futaba.unicode import normalize_caseless

logger = logging.getLogger(__name__)

__all__ = [
    'channel_name',
    'channel_mention',
    'user_mention',
    'role_mention',
    'name_discrim_search',
    'similar_names',
    'channel_name',
    'get_emoji',
    'get_user_id',
    'get_role_id',
    'get_channel_id',
    'similar_user_ids',
]

EMOJI_REGEX = re.compile(r'<:([A-Za-z0-9_\-]+(?:~[0-9]+)?):([0-9]+)>')
CHANNEL_NAME_REGEX = re.compile(r'#?([^ ]+)')
CHANNEL_MENTION_REGEX = re.compile(r'<#([0-9]+)>')
USER_MENTION_REGEX = re.compile(r'<@!?([0-9]+)>')
ROLE_MENTION_REGEX = re.compile(r'<@&([0-9]+)>')
USERNAME_DISCRIM_REGEX = re.compile(r'(.+)#([0-9]{4})')

def channel_name(name) -> Optional[str]:
    '''
    Parses a channel name, returning the name of the channel.
    The name might not correspond with an actual channel.
    '''

    logger.debug("Checking possible channel name '%s'", name)

    match = CHANNEL_NAME_REGEX.match(name)
    if match is None:
        return None

    return match[1]

def channel_mention(mention) -> Optional[int]:
    '''
    Parses a channel mention, returning the ID inside.
    The id might not correspond with an actual channel.
    '''

    logger.debug("Checking possible channel mention '%s'", mention)

    match = CHANNEL_MENTION_REGEX.match(mention)
    if match is None:
        return None

    return int(match[1])

def user_mention(mention) -> Optional[int]:
    '''
    Parses a user mention, returning the ID inside.
    The id might not correspond with an actual user.
    '''

    logger.debug("Checking possible user mention '%s'", mention)

    match = USER_MENTION_REGEX.match(mention)
    if match is None:
        return None

    return int(match[1])

def role_mention(mention) -> Optional[int]:
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

def name_discrim_search(name, users) -> Optional[discord.User]:
    '''
    Searches for a user matching the string [username]#[discriminator].
    It searches case-insensitively.
    '''

    match = USERNAME_DISCRIM_REGEX.match(name)
    if match is None:
        return None

    name, discrim = match[1], int(match[2])
    def check(user):
        uname = normalize_caseless(user.name)
        udiscrim = user.discriminator

        return name == uname and discrim == udiscrim

    name = normalize_caseless(name)
    return discord.utils.find(check, users)

def similar_names(word1, word2) -> float:
    '''
    Determines if the two strings are similar enough given the passed threshold.
    An alias for textdistance.overlap.similarity().
    '''

    return textdistance.overlap.similarity(word1, word2)

def get_emoji(name, emojis) -> Optional[Union[str, discord.Emoji]]:
    '''
    Attempts to get a discord or unicode emoji described by the given name.
    You must pass a list of all emojis the client has access to.
    '''

    logger.debug("get_emoji: checking if it's not ASCII")
    if not any(map(str.isascii, name)):
        return name

    # Search case-insensitively
    name = normalize_caseless(name)

    logger.debug("get_emoji: checking if it's an integer")
    if name.isdigit():
        id = int(name)
        try:
            return chr(id)
        except (OverflowError, ValueError):
            return discord.utils.get(emojis, id=int(name))

    logger.debug("get_emoji: checking if it's a Discord emoji mention")
    match = EMOJI_REGEX.match(name)
    if match is not None:
        return discord.utils.get(emojis, id=int(match[2]))

    logger.debug("get_emoji: checking for Discord emoji name")
    emoji = discord.utils.find(lambda e: name == normalize_caseless(e.name), emojis)
    if emoji is not None:
        return emoji

    logger.debug("get_emoji: checking if it's a unicode emoji name")
    try:
        return unicodedata.lookup(name)
    except KeyError:
        pass

    # No results
    return None

def get_user_id(name, users=()) -> Optional[int]:
    '''
    Gets a user ID from the given string 'name'.
    You can pass in a list of users for additional
    instances to search.
    '''

    # Search case-insensitively
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
    user = name_discrim_search(name, users)
    if user is not None:
        return user.id

    # Check by username
    logger.debug("get_user_id: checking if it's a username")
    user = discord.utils.find(lambda u: name == normalize_caseless(u.name), users)
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

def get_role_id(name, roles) -> Optional[int]:
    '''
    Gets a role from the given string 'name'.
    You must pass a list of roles to search from.
    '''

    # Check for role ID
    logger.debug("get_role_id: checking if it's an integer")
    if name.isdigit():
        return int(name)

    # Check for mention
    logger.debug("get_role_id: checking if it's a role mention")
    id = role_mention(name)
    if id is not None:
        return discord.utils.get(roles, id=id)

    # Check by name
    logger.debug("get_role_id: checking by name")
    role = discord.utils.get(roles, name=name)
    if role is not None:
        return role.id

    # Check by name, case-insensitive
    logger.debug("get_role_id: checking by name, case-insensitive")
    name = normalize_caseless(name)
    role = discord.utils.find(lambda r: name == normalize_caseless(r.name), roles)
    if role is not None:
        return role.id

    # No results
    logger.debug("get_role_id found no results!")
    return None

def get_channel_id(name, channels) -> Optional[int]:
    '''
    Gets a channel from the given string 'name'.
    You must pass a list of channels to search from.
    '''

    # Search case-insensitively
    name = normalize_caseless(name)

    # Check for channel ID
    logger.debug("get_channel_id: checking if it's an integer")
    if name.isdigit():
        return int(name)

    # Check for channel mention
    logger.debug("get_channel_id: checking if it's a channel mention")
    id = channel_mention(name)
    if id is not None:
        return id

    # Check by name
    logger.debug("get_channel_id: checking if it's a name")
    cname = channel_name(name)
    if cname is not None:
        channel = discord.utils.find(lambda c: name == normalize_caseless(c.name), channels)
        if channel is not None:
            return channel.id

    # No results
    logger.debug("get_channel_id found no results!")
    return None

def similar_user_ids(name, users, max_entries=5) -> Iterable[int]:
    '''
    Gets a list of user IDs that are similar to the string 'name'.
    They are ranked in order of similarity, marking users who are
    not in the this guild.
    '''

    matching_ids = []

    # Search case-insensitively
    name = normalize_caseless(name)

    # Check for user ID
    logger.debug("similar_user_ids: checking if it's an integer")
    if name.isdigit():
        matching_ids.append(int(name))

    # Check for mention
    logger.debug("similar_user_ids: checking if it's a user mention")
    id = user_mention(name)
    if id is not None:
        matching_ids.append(id)

    # Check by name#discrim
    logger.debug("similar_user_ids: checking if it's a username#discriminator")
    user = name_discrim_search(name, users)
    if user is not None:
        matching_ids.append(user.id)

    # Check by username, nickname, or username#discriminator
    logger.debug("similar_user_ids: checking usernames")
    match = USERNAME_DISCRIM_REGEX.match(name)
    check_name = name if match is None else match[1]
    similar_users = []

    for user in users:
        similar = similar_names(check_name, normalize_caseless(user.name))

        if getattr(user, 'nick', None):
            similar = max(similar, similar_names(check_name, normalize_caseless(user.nick)))

        similar_users.append((user, similar))

    # Sort by similarity
    similar_users.sort(key=lambda p: p[1], reverse=True)
    matching_ids.extend(user.id for user, similar in similar_users if similar > 0.3)

    # Done
    return islice(matching_ids, 0, max_entries)
