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
import random
import sys
from datetime import datetime
from hashlib import sha512

import discord
from discord.ext import commands

from futaba import permissions, __version__
from futaba.download import download_links
from futaba.enums import Reactions
from futaba.utils import GIT_HASH, URL_REGEX, fancy_timedelta

logger = logging.getLogger(__name__)

__all__ = [
    'Miscellaneous',
]

SHA512_ERROR_MESSAGE = 'Error downloading file'.ljust(128)

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
            ctx.send(content=f"Pong! `{ms} ms`"),
            Reactions.SUCCESS.add(ctx.message),
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
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='randomemoji', aliases=['randemoji', 'remoji'])
    async def random_emoji(self, ctx):
        '''
        Sends a random emoji from any the servers the bot is connected to.
        '''

        if not self.bot.emojis:
            await Reactions.FAIL.add(ctx.message)
            return

        await asyncio.gather(
            ctx.send(content=random.choice(self.bot.emojis)),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='sha512', aliases=['hash'])
    async def sha512(self, ctx, *urls: str):
        ''' Gives the SHA512 hashes of any files attached to the message. '''

        # Check all URLs
        for url in urls:
            if not URL_REGEX.match(url):
                await asyncio.gather(
                    ctx.send(content=f'Not a valid url: {url}'),
                    Reactions.FAIL.add(ctx.message),
                )
                return

        # Send error if no URLS
        urls = list(urls)
        urls.extend(attach.url for attach in ctx.message.attachments)
        names = list(urls)
        names.extend(attach.filename for attach in ctx.message.attachments)

        if not urls:
            await asyncio.gather(
                ctx.send(content='No URLs listed or files attached.'),
                Reactions.FAIL.add(ctx.message),
            )
            return

        # Download and check files
        lines = ['Hashes:', '```']
        buffers = await download_links(urls)
        for i, binio in enumerate(buffers):
            if binio is None:
                hashsum = SHA512_ERROR_MESSAGE
            else:
                hashsum = sha512(binio.getbuffer()).hexdigest()

            lines.append(f'{hashsum} {names[i]}')
        lines.append('```')

        await asyncio.gather(
            ctx.send(content='\n'.join(lines)),
            Reactions.SUCCESS.add(ctx.message),
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
