#
# cogs/filter/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Cog to handle text filtering, including both hard and soft enforcement,
similar unicode characters, and stripping unicode whitespace.
'''

import asyncio
import logging

import discord
from discord.ext import commands

import permissions

logger = logging.getLogger(__name__)

class FilterCog:
    __slots__ = (
        'bot',
        'filters',
    )

    def __init__(self, bot):
        self.bot = bot
        self.filters = {}

    @commands.group(name='filter')
    @commands.guild_only()
    async def filter(self, ctx):
        '''
        Adds, removes, or lists words in the filter.
        It ignores case and checks for unicode strings that look similar.
        '''

        if ctx.invoked_subcommand is None:
            # TODO send help
            pass

    @filter.group(name='server', aliases=['srv', 'guild'])
    @commands.guild_only()
    async def filter_server(self, ctx):
        '''
        Allows managing the server-wide filter.
        '''

        if ctx.subcommand_passed in ('server', 'srv', 'guild'):
            # TODO send help
            pass

    @filter_server.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def filter_server_show(self, ctx):
        '''
        List all currently filtered words in the server filter.
        '''

        # TODO
        filters = []

        if filters:
            lines = [f'Filtered words for {ctx.guild.name}:', '```']
            for filter in filters:
                lines.append(f'"{filter.text}" {filter.text!r}')
            lines.append('```')
            content = '\n'.join(lines)
        else:
            content = f'No filtered words for {ctx.guild.name}'

        await ctx.author.send(content=content)

    @commands.command(name='block', aliases=['deny', 'add', 'new'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_server_block(self, ctx, *, word: str):
        '''
        Adds the words to the server-wide filter. If a message with
        this content is found, it is deleted and the contents of
        the message are sent to the user.
        '''

        # TODO
