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
from hashlib import sha1

import discord
from discord.ext import commands

from futaba import permissions, __version__
from futaba.download import download_links
from futaba.enums import Reactions
from futaba.str_builder import StringBuilder
from futaba.utils import GIT_HASH, URL_REGEX, fancy_timedelta

logger = logging.getLogger(__name__)

__all__ = [
    'Miscellaneous',
]

SHA1_ERROR_MESSAGE = 'Error downloading file'.ljust(40)

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
        embed.add_field(name='Created by', value='[Programming Discord](https://discord.gg/010z0Kw1A9ql5c1Qe)')
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

    @commands.command(name='sha1sum', aliases=['sha1', 'sha', 'hashsum', 'hash'])
    async def sha1sum(self, ctx, *urls: str):
        ''' Gives the SHA1 hashes of any files attached to the message. '''

        # Check all URLs
        links = []
        for url in urls:
            match = URL_REGEX.match(url)
            if match is None:
                await asyncio.gather(
                    ctx.send(content=f'Not a valid url: {url}'),
                    Reactions.FAIL.add(ctx.message),
                )
                return
            links.append(match[1])
        links.extend(attach.url for attach in ctx.message.attachments)

        # Get list of "names"
        names = list(urls)
        names.extend(attach.filename for attach in ctx.message.attachments)

        # Send error if no URLS
        if not links:
            await asyncio.gather(
                ctx.send(content='No URLs listed or files attached.'),
                Reactions.FAIL.add(ctx.message),
            )
            return

        # Download and check files
        contents = []
        content = StringBuilder('Hashes:\n```')
        buffers = await download_links(links)
        for i, binio in enumerate(buffers):
            if binio is None:
                hashsum = SHA1_ERROR_MESSAGE
            else:
                hashsum = sha1(binio.getbuffer()).hexdigest()

            content.writeln(f'{hashsum} {names[i]}')
            if len(content) > 1920:
                contents.append(content)
                if i < len(buffers) - 1:
                    content.clear()
                    content.writeln('```')

        if len(content) > 4:
            content.writeln('```')
            contents.append(content)

        async def send_messages():
            for content in contents:
                await ctx.send(content=str(content))

        await asyncio.gather(
            send_messages(),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='shutdown', aliases=['halt'])
    @permissions.check_owner()
    async def shutdown(self, ctx):
        ''' Shuts down the bot. Can only able be run by an owner. '''

        self.journal.send('admin/shutdown', ctx.guild, 'Shutting down bot', icon='shutdown')
        await Reactions.SUCCESS.add(ctx.message)
        exit()
