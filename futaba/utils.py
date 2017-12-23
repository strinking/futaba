#
# utils.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# mawabot is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging
import unicodedata

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

COGS_DIR = 'futaba.cogs.'

__all__ = [
    'Reloader',
    'normalize_caseless',
]

class Reloader:

    def __init__(self, bot):
        self.bot = bot

    def load_cog(self, cogname):
        if COGS_DIR not in cogname:
            cogname = f'{COGS_DIR}{cogname}'
        self.bot.load_extension(cogname)

    def unload_cog(self, cogname):
        if COGS_DIR not in cogname:
            cogname = f'{COGS_DIR}{cogname}'
        self.bot.unload_extension(cogname)

    @commands.command()
    async def load(self, ctx, cogname: str):
        ''' Loads the cog given '''

        logger.info(f'Cog load requested: {cogname}')

        # Load cog
        try:
            self.load_cog(cogname)
        except Exception as error:
            logger.error('Load failed')
            logger.debug('Reason:', exc_info=error)
            await self.bot._react_not_complete(ctx.message)
            embed = discord.Embed(color=discord.Color.red(), description=f'```{error}```')
            embed.set_author(name='Load failed')
            await self.bot._send(embed=embed)
        else:
            logger.info(f'Loaded cog: {cogname}')
            await self.bot._react_complete(ctx.message)
            embed = discord.Embed(color=discord.Color.green(), description=f'```{cogname}```')
            embed.set_author(name='Loaded')
            await self.bot._send(embed=embed)

    @commands.command()
    async def unload(self, ctx, cogname: str):
        ''' Unloads the cog given '''

        logger.info(f'Cog unload requested: {cogname}')

        # Load cog
        try:
            self.unload_cog(cogname)
        except Exception as error:
            logger.error('Unload failed')
            logger.debug('Reason:', exc_info=error)
            await self.bot._react_not_complete(ctx.message)
            embed = discord.Embed(color=discord.Color.red(), description=f'```{error}```')
            embed.set_author(name='Unload failed')
            await self.bot._send(embed=embed)
        else:
            logger.info(f'Unloaded cog: {cogname}')
            await self.bot._react_complete(ctx.message)
            embed = discord.Embed(color=discord.Color.green(), description=f'```{cogname}```')
            embed.set_author(name='Unloaded')
            await self.bot._send(embed=embed)

    @commands.command()
    async def reload(self, ctx, cogname: str):
        ''' Reloads the cog given '''

        logger.info(f'Cog reload requested: {cogname}')

        # Load cog
        try:
            self.unload_cog(cogname)
            self.load_cog(cogname)
        except Exception as error:
            logger.error('Reload failed')
            logger.debug('Reason:', exc_info=error)
            await self.bot._react_not_complete(ctx.message)
            embed = discord.Embed(color=discord.Color.red(), description=f'```{error}```')
            embed.set_author(name='Reload failed')
            await self.bot._send(embed=embed)
        else:
            logger.info(f'Reloaded cog: {cogname}')
            await self.bot._react_complete(ctx.message)
            embed = discord.Embed(color=discord.Color.green(), description=f'```{cogname}```')
            embed.set_author(name='Reloaded')
            await self.bot._send(embed=embed)

def normalize_caseless(s):
    return unicodedata.normalize('NFKD', s.casefold())
    