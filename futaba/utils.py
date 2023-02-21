#
# utils.py
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
import subprocess
from datetime import datetime
from io import BytesIO
from itertools import zip_longest

import discord

from futaba.str_builder import StringBuilder

logger = logging.getLogger(__name__)

__all__ = [
    "GIT_HASH",
    "URL_REGEX",
    "Dummy",
    "DictEmbed",
    "class_property",
    "fancy_timedelta",
    "async_partial",
    "map_or",
    "if_not_null",
    "copy_discord_file",
    "first",
    "chunks",
    "partition_on",
    "lowerbool",
    "plural",
    "user_discrim",
    "escape_backticks",
]


def _get_git_hash():
    try:
        output = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        return output.decode("utf-8").strip()
    except FileNotFoundError:
        logger.warning("'git' binary not found")
    except subprocess.CalledProcessError:
        logger.warning("Unable to call 'git rev-parse --short HEAD'")

    return ""


GIT_HASH = _get_git_hash()

URL_REGEX = re.compile(
    r"<?(https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b(?:[-a-zA-Z0-9@:%_\+.~#?&//=]*))>?"
)


class Dummy:
    """Dummy class that can freely be assigned any fields or members."""

    # - pass -


class DictEmbed:
    """
    A discord.Embed-like wrapper which just holds the JSON-compatible dictionary
    and returns that on 'conversion'.
    """

    __slots__ = ("dict",)

    def __init__(self, dict):
        self.dict = dict

    def to_dict(self):
        return self.dict


class class_property(property):
    def __get__(self, cls, owner):
        # pylint: disable=no-member
        return self.fget.__get__(None, owner)()


def fancy_timedelta(delta):
    """
    Formats a fancy time difference.
    When given a datetime object, it calculates the difference from the present.
    """

    if isinstance(delta, datetime):
        delta = abs(datetime.now() - delta)

    result = StringBuilder(sep=" ")
    years, days = divmod(delta.days, 365)
    months, days = divmod(days, 30)
    weeks, days = divmod(days, 7)
    hours, seconds = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    seconds += delta.microseconds / 1e6
    seconds = round(seconds, 2)

    if years:
        result.write(f"{years}y")
    if months:
        result.write(f"{months}mo")
    if weeks:
        result.write(f"{weeks}w")
    if days:
        result.write(f"{days}d")
    if hours:
        result.write(f"{hours}h")
    if minutes:
        result.write(f"{minutes}m")
    if seconds:
        result.write(f"{seconds}s")

    return str(result)


def async_partial(coro, *added_args, **added_kwargs):
    """Like functools.partial(), but for coroutines."""

    async def wrapped(*args, **kwargs):
        return await coro(*added_args, *args, **added_kwargs, **kwargs)

    return wrapped


def map_or(func, obj):
    """Applies func to obj if it is not None."""

    if obj is None:
        return obj

    return func(obj)


def if_not_null(obj, alt):
    """Returns 'obj' if it's not None, 'alt' otherwise."""

    if obj is None:
        if callable(alt):
            return alt()
        else:
            return alt

    return obj


def copy_discord_file(file: discord.File):
    if isinstance(file.fp, str):
        # Copying is unnecessary, it's going to read from disk
        return file

    new_buffer = BytesIO(file.fp.getbuffer().tobytes())
    return discord.File(new_buffer, file.filename)


def first(iterable, default=None):
    """
    Returns the first item in the iterable that is truthy.
    If none, then return 'default'.
    """

    for item in iterable:
        if item:
            return item
    return default


def chunks(iterable, count, fillvalue=None):
    """Iterate over the iterable in 'count'-long chunks."""

    args = [iter(iterable)] * count
    return zip_longest(*args, fillvalue=fillvalue)


def partition_on(predicate, iterable, map_fn=None):
    """Partition an iterable into two lists on the return type of the predicate."""

    left, right = [], []

    if map_fn is None:
        for i in iterable:
            if predicate(i):
                left.append(i)
            else:
                right.append(i)
    else:
        for i in iterable:
            if predicate(i):
                left.append(map_fn(i))
            else:
                right.append(map_fn(i))

    return left, right


def lowerbool(value):
    """Returns 'true' if the expression is true, and 'false' if not."""

    return "true" if value else "false"


def plural(num):
    """Gets the English plural ending for an ordinal number."""

    return "" if num == 1 else "s"


def user_discrim(user):
    """
    Return the user's username and disc
    in the format <username>#<discriminator>
    """

    return f"{user.name}#{user.discriminator}"


def escape_backticks(content):
    """
    Replace any backticks in 'content' with a unicode lookalike to allow
    quoting in Discord.
    """

    return content.replace("`", "\N{ARMENIAN COMMA}").replace(":", "\N{RATIO}")
