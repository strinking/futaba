#
# utils.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
import string
import unicodedata
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__name__)

COGS_DIR = 'futaba.cogs.'

__all__ = [
    'READABLE_CHAR_SET',
    'Dummy',
    'Reloader',
    'normalize_caseless',
    'fancy_timedelta',
    'async_partial',
    'plural',
    'if_not_null',
    'unicode_repr',
]

READABLE_CHAR_SET = frozenset(string.printable) - frozenset('\t\n\r\x0b\x0c')

class Dummy:
    '''
    Dummy class that can freely be assigned any fields or members.
    '''

    pass

class Reloader:
    '''
    Special cog that is used to load, unload, and reload all other cogs.
    '''

    def __init__(self, bot):
        self.bot = bot

    def load_cog(self, cogname):
        if not cogname.startswith(COGS_DIR):
            cogname = f'{COGS_DIR}{cogname}'
        self.bot.load_extension(cogname)

    def unload_cog(self, cogname):
        if not cogname.startswith(COGS_DIR):
            cogname = f'{COGS_DIR}{cogname}'
        self.bot.unload_extension(cogname)

    @commands.command()
    @permissions.check_owner()
    async def load(self, ctx, cogname: str):
        ''' Loads the given cog '''

        logger.info("Cog load requested: %s", cogname)

        try:
            self.load_cog(cogname)
        except Exception as error:
            logger.error("Loading cog %s failed", cogname, exc_info=error)
            embed = discord.Embed(color=discord.Color.red(), description=f'```{error}```')
            embed.set_author(name='Load failed')
            await asyncio.gather(
                self.bot._send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )

        else:
            logger.info("Loaded cog: %s", cogname)
            embed = discord.Embed(color=discord.Color.green(), description=f'```{cogname}```')
            embed.set_author(name='Loaded')
            await asyncio.gather(
                self.bot._send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )

    @commands.command()
    @permissions.check_owner()
    async def unload(self, ctx, cogname: str):
        ''' Unloads the cog given '''

        logger.info("Cog unload requested: %s", cogname)

        try:
            self.unload_cog(cogname)
        except Exception as error:
            logger.error("Unloading cog %s failed", cogname, exc_info=error)
            embed = discord.Embed(color=discord.Color.red(), description=f'```{error}```')
            embed.set_author(name='Unload failed')
            await asyncio.gather(
                self.bot._send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
        else:
            logger.info("Unloaded cog: %s", cogname)
            embed = discord.Embed(color=discord.Color.green(), description=f'```{cogname}```')
            embed.set_author(name='Unloaded')
            await asyncio.gather(
                self.bot._send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )

    @commands.command()
    @permissions.check_owner()
    async def reload(self, ctx, cogname: str):
        ''' Reloads the cog given '''

        logger.info("Cog reload requested: %s", cogname)

        # Load cog
        try:
            self.unload_cog(cogname)
            self.load_cog(cogname)
        except Exception as error:
            logger.error("Reloading cog %s failed", cogname, exc_info=error)
            embed = discord.Embed(color=discord.Color.red(), description=f'```{error}```')
            embed.set_author(name='Reload failed')
            await asyncio.gather(
                self.bot._send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
        else:
            logger.info("Reloaded cog: %s", cogname)
            embed = discord.Embed(color=discord.Color.green(), description=f'```{cogname}```')
            embed.set_author(name='Reloaded')
            await asyncio.gather(
                self.bot._send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )

    @commands.command()
    async def listcogs(self, ctx):
        '''
        List the cogs that are currently loaded
        '''

        lines = ['```yaml', 'Cogs loaded:']

        if self.bot.cogs:
            for cog in self.bot.cogs:
                lines.append(f' - {cog}')
        else:
            lines.append(' - (none)')

        lines.append('```')
        await ctx.send('\n'.join(lines))

def normalize_caseless(s):
    '''
    Shifts the string into a uniform case (lower-case),
    but also accounting for unicode characters. Used
    for case-insenstive comparisons.
    '''

    return unicodedata.normalize('NFKD', s.casefold())

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
    return f'{", ".join(parts)} and {seconds} second{plural(seconds)}'

def async_partial(coro, *added_args, **added_kwargs):
    '''
    Like functools.partial(), but for coroutines.
    '''

    async def wrapped(*args, **kwargs):
        return await coro(*added_args, *args, **added_kwargs, **kwargs)
    return wrapped

def plural(num):
    '''
    Gets the English plural ending for an ordinal number.
    '''

    return '' if num == 1 else 's'

def if_not_null(obj, alt):
    '''
    Returns 'obj' if it's not None, 'alt' otherwise.
    '''

    if obj is None:
        if callable(alt):
            return alt()
        else:
            return alt

    return obj

def unicode_repr(s):
    '''
    Similar to repr(), but always escapes characters that aren't "readable".
    That is, any characters not in READABLE_CHAR_SET.
    '''

    parts = []
    for ch in s:
        if ch == '\n':
            parts.append('\\n')
        elif ch == '\t':
            parts.append('\\t')
        elif ch == '"':
            parts.append('\\"')
        elif ch in READABLE_CHAR_SET:
            parts.append(ch)
        else:
            num = ord(ch)
            if num < 0x100:
                parts.append(f'\\x{num:02x}')
            elif num < 0x10000:
                parts.append(f'\\u{num:04x}')
            elif num < 0x100000000:
                parts.append(f'\\U{num:08x}')
            else:
                raise ValueError(f"Character {ch!r} (ord {num:x}) too big for escaping")

    escaped = ''.join(parts)
    return f'"{escaped}"'
