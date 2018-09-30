#
# similar.py
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
from itertools import islice
from typing import Iterable, Optional, Union

import discord
import textdistance

from futaba.unicode import normalize_caseless

logger = logging.getLogger(__name__)

__all__ = [
    'similar_names',
    'similar_user_ids',
]

def similar_names(word1, word2) -> float:
    '''
    Determines if the two strings are similar enough given the passed threshold.
    An alias for textdistance.overlap.similarity().
    '''

    return textdistance.overlap.similarity(word1, word2)

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
