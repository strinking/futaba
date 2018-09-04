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
import unicodedata

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__name__)

COGS_DIR = 'futaba.cogs.'

__all__ = [
    'Reloader',
    'normalize_caseless',
    'plural',
]

class Reloader:
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

def plural(num):
    '''
    Gets the English plural ending for an ordinal number.
    '''

    return '' if num == 1 else 's'
