#
# cogs/journal/core.py
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
Cog for configuring Futaba journalling output, directing certain kinds
of messages to different logging channels.
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions
from futaba.journal import ChannelOutputListener, Router

logger = logging.getLogger(__name__)

__all__ = [
    'Journal',
]

class Journal:
    __slots__ = (
        'bot',
        'router',
    )

    def __init__(self, bot):
        self.bot = bot
        self.router = Router()
        bot.journal_cog = self

        logger.info("Loading journal output channels from the database")
        with bot.sql.transaction():
            for guild in bot.guilds:
                for output in bot.sql.journal.get_journal_channels(guild):
                    logger.info("Registering journal channel #%s (%d) for path '%s'",
                            output.channel.name, output.channel.id, output.path)
                    self.router.register(ChannelOutputListener(self.router, output.path, output.channel))
        self.router.start(bot.loop)

    @commands.group(name='journal', aliases=['log'])
    async def log(self, ctx):
        ''' Configure channel output for bot journal events. '''

        if ctx.invoked_subcommand is None:
            # TODO send help
            await Reactions.FAIL.add(ctx.message)

    @log.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_show(self, ctx):
        ''' Displays current settings for this guild '''

        outputs = self.bot.sql.journal.get_journal_channels(ctx.guild)
        outputs.sort(key=lambda x: x.channel.name)
        lines = []
        attributes = []
        for output in outputs:
            if not output.settings.recursive:
                attributes.append('exact path')

            attributes_str = f'({", ".join(attributes)})' if attributes else ''
            lines.append(f'- `{output.path}` mounted at {output.channel.mention} {attributes_str}')
            attributes.clear()

        if lines:
            embed = discord.Embed(colour=discord.Colour.teal(), description='\n'.join(lines))
            embed.set_author(name='Current journal outputs')
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name=f'No journal outputs!')

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    def log_updated_message(self, channel):
        outputs = list(self.bot.sql.journal.get_journals_on_channel(channel))
        if outputs:
            paths = ' '.join(f'`{output.path}`' for output in outputs)
        else:
            paths = '(none)'
        return f'Channel outputs updated! Current journal paths: {paths}'

    @log.command(name='add', aliases=['append', 'extend', 'new', 'set', 'update'])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_add(self, ctx, channel: discord.TextChannel, path: str, *flags: str):
        '''
        Add a journal logger to the channel for the given path.
        Accepts the optional flags:
            -exact, Don't recursively accept journal events from children.
        '''

        logging.info("Adding journal logger for channel #%s (%d) on path '%s'",
                channel.name, channel.id, path)
        recursive = True

        for flag in flags:
            if flag == '-exact':
                recursive = False
            else:
                await asyncio.gather(
                    Reactions.FAIL.add(ctx.message),
                    ctx.send(content=f'No such flag: `{flag}`')
                )
                return

        logger.debug("Registering route")
        self.router.register(ChannelOutputListener(self.router, path, channel))

        logger.debug("Updating database for channel output")
        with self.bot.sql.transaction():
            journal_sql = self.bot.sql.journal
            if journal_sql.has_journal_channel(channel, path):
                journal_sql.update_journal_channel(channel, path, recursive)
            else:
                journal_sql.add_journal_channel(channel, path, recursive)

        await asyncio.gather(
            channel.send(content=self.log_updated_message(channel)),
            Reactions.SUCCESS.add(ctx.message),
        )

    @log.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_remove(self, ctx, channel: discord.TextChannel, path: str):
        '''
        Removes a journal logger for the given path from the channel.
        '''

        logging.info("Removing journal logger for channel #%s (%d) from path '%s'",
                channel.name, channel.id, path)

        listener = self.router.get(path, channel=channel)
        if listener is None:
            # No listener found
            await asyncio.gather(
                ctx.send(content=f'No output on `{path}` found for {channel.mention}'),
                Reactions.FAIL.add(ctx.message),
            )
            return

        self.router.unregister(listener)

        with self.bot.sql.transaction():
            self.bot.sql.journal.delete_journal_channel(channel, path)

        await asyncio.gather(
            channel.send(content=self.log_updated_message(channel)),
            Reactions.SUCCESS.add(ctx.message),
        )

    @log.command(name='send', aliases=['broadcast'])
    @commands.guild_only()
    @permissions.check_mod()
    async def log_send(self, ctx, path: str, content: str, *attributes: str):
        '''
        Manually send a journal event to test logging channels.
        The content must be a single argument, wrapped in quotes if
        it has spaces, and you can specify a number of journal attributes
        in the form KEY=VALUE.
        '''

        if path == '/':
            await asyncio.gather(
                ctx.send(content='Cannot broadcast on /'),
                Reactions.FAIL.add(ctx.message),
            )
            return

        journal_attributes = {}
        for attribute in attributes:
            try:
                key, value = attribute.split('=')
                journal_attributes[key] = value
            except ValueError:
                await asyncio.gather(
                    ctx.send(content='All attributes must be in the form KEY=VALUE'),
                    Reactions.FAIL.add(ctx.message),
                )
                return

        logging.info("Sending manual journal event: '%s' (attrs: %s)", content, journal_attributes)
        self.bot.get_broadcaster(path).send('', ctx.guild, content, **journal_attributes)
