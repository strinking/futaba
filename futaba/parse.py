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
from itertools import islice

import discord
import textdistance

from futaba.utils import normalize_caseless

logger = logging.getLogger(__name__)

__all__ = [
    'channel_mention',
    'user_mention',
    'role_mention',
    'name_discrim_search',
    'similar_names',
    'get_user_id',
    'similar_user_ids',
]

CHANNEL_MENTION_REGEX = re.compile(r'<#([0-9]+)>')
USER_MENTION_REGEX = re.compile(r'<@!?([0-9]+)>')
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

def name_discrim_search(name, users):
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

def similar_names(word1, word2):
    '''
    Determines if the two strings are similar enough given the passed threshold.
    An alias for textdistance.overlap.similarity().
    '''

    return textdistance.overlap.similarity(word1, word2)

def get_user_id(name, users=()):
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

def similar_user_ids(name, users, max_entries=5):
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
