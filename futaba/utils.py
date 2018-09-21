#
# utils.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
import re
import subprocess
from datetime import datetime
from itertools import zip_longest

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__name__)

__all__ = [
    'GIT_HASH',
    'URL_REGEX',
    'Dummy',
    'fancy_timedelta',
    'async_partial',
    'first',
    'chunks',
    'lowerbool',
    'plural',
    'user_discrim',
    'escape_backticks',
    'if_not_null',
]

def _get_git_hash():
    try:
        output = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'])
        return output.decode('utf-8').strip()
    except FileNotFoundError:
        logger.warning("'git' binary not found")
    except subprocess.CalledProcessError:
        logger.warning("Unable to call 'git rev-parse --short HEAD'")

    return ''

GIT_HASH = _get_git_hash()

URL_REGEX = re.compile(
    r'https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*)'
)

class Dummy:
    '''
    Dummy class that can freely be assigned any fields or members.
    '''

    pass

def fancy_timedelta(delta):
    '''
    Formats a fancy time difference.
    When given a datetime object, it calculates the difference from the present.
    '''

    if isinstance(delta, datetime):
        delta = datetime.now() - delta

    parts = []
    years, days = divmod(delta.days, 365)
    months, days = divmod(days, 30)
    weeks, days = divmod(days, 7)
    hours, seconds = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)

    if years:
        parts.append(f'{years} year{plural(years)}')
    if months:
        parts.append(f'{months} month{plural(months)}')
    if weeks:
        parts.append(f'{weeks} week{plural(weeks)}')
    if days:
        parts.append(f'{days} day{plural(days)}')
    if hours:
        parts.append(f'{hours} hour{plural(hours)}')
    if minutes:
        parts.append(f'{minutes} minute{plural(minutes)}')

    seconds += delta.microseconds / 1e6
    seconds_str = f'{seconds} second{plural(seconds)}'

    if parts:
        return f'{", ".join(parts)} and {seconds_str}'
    else:
        return seconds_str

def async_partial(coro, *added_args, **added_kwargs):
    ''' Like functools.partial(), but for coroutines. '''

    async def wrapped(*args, **kwargs):
        return await coro(*added_args, *args, **added_kwargs, **kwargs)
    return wrapped

def first(iterable, default=None):
    '''
    Returns the first item in the iterable that is truthy.
    If none, then return 'default'.
    '''

    for item in iterable:
        if item:
            return item
    return default

def chunks(iterable, count, fillvalue=None):
    ''' Iterate over the iterable in 'count'-long chunks. '''

    args = [iter(iterable)] * count
    return zip_longest(*args, fillvalue=fillvalue)

def lowerbool(value):
    ''' Returns 'true' if the expression is true, and 'false' if not. '''

    return 'true' if value else 'false'

def plural(num):
    ''' Gets the English plural ending for an ordinal number. '''

    return '' if num == 1 else 's'

def user_discrim(user):
    '''
    Return the user's username and disc
    in the format <username>#<discriminator>
    '''

    return f'{user.name}#{user.discriminator}'

def escape_backticks(content):
    '''
    Replace any backticks in 'content' with a unicode lookalike to allow
    quoting in Discord.
    '''

    return content.replace('`', '\N{ARMENIAN COMMA}').replace(':', '\N{RATIO}')

def if_not_null(obj, alt):
    ''' Returns 'obj' if it's not None, 'alt' otherwise. '''

    if obj is None:
        if callable(alt):
            return alt()
        else:
            return alt

    return obj
