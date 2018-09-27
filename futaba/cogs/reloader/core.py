#
# cogs/reloader/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Cog for loading, unloading, or reloading other cogs.
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions
from futaba.str_builder import StringBuilder

COGS_DIR = 'futaba.cogs.'

logger = logging.getLogger(__name__)

__all__ = [
    'Reloader',
]

class Reloader:
    __slots__ = (
        'bot',
        'journal',
    )

    MANDATORY_COGS = ('journal', 'reloader')

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/cog')

    def load_cog(self, cogname):
        if not cogname.startswith(COGS_DIR):
            cogname = f'{COGS_DIR}{cogname}'
        self.bot.load_extension(cogname)

    def unload_cog(self, cogname):
        if not cogname.startswith(COGS_DIR):
            cogname = f'{COGS_DIR}{cogname}'
        self.bot.unload_extension(cogname)

    @commands.command(name='load', aliases=['l'])
    @permissions.check_owner()
    async def load(self, ctx, cogname: str):
        ''' Loads the named cog. '''

        logger.info("Cog load requested: %s", cogname)

        if cogname in Reloader.MANDATORY_COGS:
            logger.info("Cog cannot be loaded because it is mandatory")
            embed = discord.Embed(colour=discord.Colour.dark_red())
            embed.set_author(name='Cannot load')
            embed.description = 'Cog cannot be loaded because it is mandatory'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            content = f'Unable to load cog {cogname} because it is mandatory'
            self.journal.send('load/fail', ctx.guild, content, icon='cog',
                    cogname=cogname, reason='mandatory')
            return

        try:
            self.load_cog(cogname)
        except Exception as error:
            logger.error("Loading cog %s failed", cogname, exc_info=error)
            embed = discord.Embed(colour=discord.Colour.dark_red(), description=f'```\n{error}\n```')
            embed.set_author(name='Load failed')
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            content = f'Error while trying to load cog {cogname}'
            self.journal.send('load/fail', ctx.guild, content, icon='cog',
                    cogname=cogname, reason='error', error=error)
        else:
            logger.info("Loaded cog: %s", cogname)
            embed = discord.Embed(colour=discord.Colour.green(), description=f'```\n{cogname}\n```')
            embed.set_author(name='Loaded')
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )
            content = f'Successfully loaded cog {cogname}'
            self.journal.send('load', ctx.guild, content, icon='cog', cogname=cogname)

    @commands.command(name='unload', aliases=['ul'])
    @permissions.check_owner()
    async def unload(self, ctx, cogname: str):
        ''' Unloads the named cog. '''

        logger.info("Cog unload requested: %s", cogname)

        if cogname in Reloader.MANDATORY_COGS:
            logger.info("Cog cannot be unloaded because it is mandatory")
            embed = discord.Embed(colour=discord.Colour.dark_red())
            embed.set_author(name='Cannot unload')
            embed.description = 'Cog cannot be unloaded because it is mandatory'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            content = f'Unable to unload cog {cogname} because it is mandatory'
            self.journal.send('unload/fail', ctx.guild, content, icon='cog',
                    cogname=cogname, reason='mandatory')
            return

        try:
            self.unload_cog(cogname)
        except Exception as error:
            logger.error("Unloading cog %s failed", cogname, exc_info=error)
            embed = discord.Embed(colour=discord.Colour.dark_red(), description=f'```\n{error}\n```')
            embed.set_author(name='Unload failed')
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            content = f'Error while trying to unload cog {cogname}'
            self.journal.send('unload/fail', ctx.guild, content, icon='cog',
                    cogname=cogname, reason='error', error=error)
        else:
            logger.info("Unloaded cog: %s", cogname)
            embed = discord.Embed(colour=discord.Colour.green(), description=f'```\n{cogname}\n```')
            embed.set_author(name='Unloaded')
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )
            content = f'Successfully unloaded cog {cogname}'
            self.journal.send('unload', ctx.guild, content, icon='cog', cogname=cogname)

    @commands.command(name='reload', aliases=['rl'])
    @permissions.check_owner()
    async def reload(self, ctx, cogname: str):
        ''' Reloads the named cog. '''

        logger.info("Cog reload requested: %s", cogname)

        if cogname in Reloader.MANDATORY_COGS:
            logger.info("Cog cannot be reloaded because it is mandatory")
            embed = discord.Embed(colour=discord.Colour.dark_red())
            embed.set_author(name='Cannot reload')
            embed.description = 'Cog cannot be reloaded because it is mandatory'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            content = f'Unable to reload cog {cogname} because it is mandatory'
            self.journal.send('reload/fail', ctx.guild, content, icon='cog',
                    cogname=cogname, reason='mandatory')
            return

        try:
            self.unload_cog(cogname)
            self.load_cog(cogname)
        except Exception as error:
            logger.error("Reloading cog %s failed", cogname, exc_info=error)
            embed = discord.Embed(colour=discord.Colour.dark_red(), description=f'```\n{error}\n```')
            embed.set_author(name='Reload failed')
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            content = f'Error while trying to reload cog {cogname}'
            self.journal.send('reload/fail', ctx.guild, content, icon='cog',
                    cogname=cogname, reason='error', error=error)
        else:
            logger.info("Reloaded cog: %s", cogname)
            embed = discord.Embed(colour=discord.Colour.green(), description=f'```\n{cogname}\n```')
            embed.set_author(name='Reloaded')
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )
            content = f'Successfully reloaded cog {cogname}'
            self.journal.send('reload', ctx.guild, content, icon='cog', cogname=cogname)

    @commands.command(name='listcogs', aliases=['cogs'])
    async def listcogs(self, ctx):
        ''' Lists all currently loaded cogs. '''

        content = StringBuilder('```yaml\nCogs loaded:\n')
        if self.bot.cogs:
            for cog in sorted(self.bot.cogs):
                content.writeln(f' - {cog}')
        else:
            content.writeln(' - (none)')

        content.writeln('```')
        await ctx.send(content=str(content))
