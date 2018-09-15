#
# cogs/misc/core.py
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
Cog for misceallaneous commands that don't really belong anywhere else.
'''

import asyncio
import logging
import sys
from datetime import datetime

import discord
from discord.ext import commands

from futaba import permissions, __version__
from futaba.enums import Reactions
from futaba.utils import GIT_HASH, fancy_timedelta

logger = logging.getLogger(__name__)

__all__ = [
    'Miscellaneous',
]

class Miscellaneous:
    __slots__ = (
        'bot',
        'journal',
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/misc')

    @commands.command(name='ping')
    async def ping(self, ctx):
        ''' Determines the bot's current latency. '''

        duration = datetime.now() - discord.utils.snowflake_time(ctx.message.id)
        ms = duration.microseconds / 1000

        await asyncio.gather(
            Reactions.SUCCESS.add(ctx.message),
            ctx.send(content=f"Pong! `{ms} ms`")
        )

    @commands.command(name='about', aliases=['aboutme', 'botinfo'])
    async def about(self, ctx):
        ''' Prints information about the running bot. '''

        pyver = sys.version_info
        python_emoji = self.bot.get_emoji(490419105699069952) or ''
        discord_emoji = self.bot.get_emoji(490419059964510210) or ''

        embed = discord.Embed()
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=f'Futaba v{__version__} {GIT_HASH}')
        embed.add_field(name='Running for', value=fancy_timedelta(self.bot.uptime))
        embed.add_field(name='Created by', value='https://discord.gg/010z0Kw1A9ql5c1Qe')
        embed.add_field(name='Source code', value='https://github.com/strinking/futaba')
        embed.description = '\n'.join((
            f'{python_emoji} Powered by Python {pyver.major}.{pyver.minor}.{pyver.micro}',
            f'{discord_emoji} Using discord.py {discord.__version__}',
        ))

        if ctx.guild is not None:
            embed.colour = ctx.guild.me.colour

        await asyncio.gather(
            Reactions.SUCCESS.add(ctx.message),
            ctx.send(embed=embed),
        )

    @commands.command(name='shutdown', aliases=['halt'])
    @permissions.check_owner()
    async def shutdown(self, ctx):
        '''
        Shuts down the bot. Only able to be run by an owner.
        '''

        self.journal.send('admin/shutdown', ctx.guild, 'Shutting down bot', icon='shutdown')
        await Reactions.SUCCESS.add(ctx.message)
        exit()
