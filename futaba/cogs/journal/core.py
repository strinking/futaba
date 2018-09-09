#
# cogs/journal/core.py
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
Cog for configuring Futaba journalling output, directing certain kinds
of messages to different logging channels.
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__name__)

__all__ = [
    'Journal',
]

class Journal:
    __slots__ = (
        'bot',
    )

    def __init__(self, bot):
        self.bot = bot

    @commands.group(name='journal', aliases=['log'])
    async def log(self, ctx):
        ''' Configure channel output for bot journal events. '''

        if ctx.invoked_subcommand is None:
            # TODO send help
            await Reactions.FAIL.add(ctx.message)

    @log.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    @permissions.check_admin()
    async def log_show(self, ctx):
        ''' Displays current settings for this guild '''

        # TODO store settings in DB
        # TODO retrieve settings on load
        # TODO allow per-guild querying
        # TODO add logging.info() calls to commands
        await Reactions.FAIL.add(ctx.message)

    @log.command(name='add', aliases=['append', 'extend', 'new'])
    @commands.guild_only()
    @permissions.check_admin()
    async def log_add(self, ctx, channel: discord.TextChannel, path: str, *flags: str):
        '''
        Add a journal logger to the channel for the given path.
        Accepts the optional flags:
            -exact, Don't recursively accept journal events from children.
        '''

        recursive = True

        for flag in flags:
            if flag == '-exact':
                recursive = False
            else:
                await asyncio.gather(
                    Reactions.FAIL.add(ctx.message),
                    ctx.send(content=f'No such flag: {flag}')
                )
                return

        # TODO add
        await Reactions.FAIL.add(ctx.message)

    @log.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_admin()
    async def log_remove(self, ctx, channel: discord.TextChannel, path: str):
        '''
        Removes a journal logger for the given path from the channel.
        '''

        # TODO remove
        await Reactions.FAIL.add(ctx.message)
