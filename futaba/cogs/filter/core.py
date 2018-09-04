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
from collections import defaultdict

import discord
from discord.ext import commands

from futaba import permissions
from .filter import Filter, FilterType
from .utils import Reactions

logger = logging.getLogger(__name__)

__all__ = [
    'FilterCog',
]

class FilterCog:
    __slots__ = (
        'bot',
        'filters',
    )

    def __init__(self, bot):
        self.bot = bot
        self.filters = defaultdict(lambda: {filter_type: set() for filter_type in FilterType})

    async def add_filter(self, message, location, level, text):
        logger.info("Adding %r to server filter '%s' for '%s' (%d)",
                text, level, location.name, location.id)

        try:
            with self.bot.sql.transaction():
                try:
                    self.bot.sql.filter.add_filter(location, level, text)
                except ValueError:
                    # Filter already exists
                    self.bot.sql.filter.update_filter(location, level, text)
        except Exception as error:
            logger.error("Error adding filter", exc_info=error)
            await message.add_reaction(Reactions.FAIL)
        else:
            self.filters[location][level].add(Filter(text))
            await message.add_reaction(Reactions.SUCCESS)

    async def delete_filter(self, message, location, text):
        logger.info("Removing %r from server filter for '%s' (%d)", text, location.name, location.id)

        with self.bot.sql.transaction():
            try:
                if self.bot.sql.filter.delete_filter(location, text):
                    logger.debug("Succesfully removed filter")
                    await message.add_reaction(Reactions.SUCCESS)
                else:
                    logger.debug("Filter was not present, deletion failed")
                    await message.add_reaction(Reactions.FAIL)
            except:
                logger.error("Error deleting filter", exc_info=1)
                await message.add_reaction(Reactions.FAIL)

    async def show_filter(self, message, author, location_name, all_filters):
        if all_filters:
            contents = []
            lines = [f'Filtered strings for {location_name}:']

            for filter_type, filters in all_filters.items():
                lines.append(f'{filter_type.emoji} {filter_type.description} {filter_type.emoji})')
                lines.append('```')
                current_len = sum(len(line) for line in lines)

                for filter in filters:
                    line = f'- "{filter.text}" {filter.text!r}'
                    current_len += len(line)

                    if current_len > 1800:
                        # Too long, break into new message
                        lines.append('```')
                        contents.append('\n'.join(lines))

                        # Start lines over
                        lines.clear()
                        lines.append('```')
                        lines.append(line)
                        current_len = len(line)
                    else:
                        lines.append(line)

                lines.append('```')
                contents.append('\n'.join(lines))
                lines.clear()
        else:
            contents = [f'No filtered strings for {location_name}']

        async def post_all():
            for content in contents:
                await author.send(content=content)

        await asyncio.gather(
            post_all(),
            message.add_reaction(Reactions.SUCCESS),
        )

    @commands.group(name='filter')
    @commands.guild_only()
    async def filter(self, ctx):
        '''
        Adds, removes, or lists words in the filter.
        It ignores case and checks for unicode strings that look similar.
        '''

        if ctx.invoked_subcommand is None:
            # TODO send help
            await ctx.message.add_reaction(Reactions.FAIL)

    @filter.group(name='server', aliases=['srv', 's', 'guild', 'g'])
    @commands.guild_only()
    async def filter_guild(self, ctx):
        '''
        Allows managing the server-wide filter.
        '''

        if ctx.subcommand_passed in ('server', 'srv', 's', 'guild', 'g'):
            # TODO send help
            await ctx.message.add_reaction(Reactions.FAIL)

    @filter_guild.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def filter_guild_show(self, ctx):
        '''
        List all currently filtered words in the server filter.
        '''

        await self.show_filter(ctx.message, ctx.author, ctx.guild.name, self.filters[ctx.guild])

    @filter_guild.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_remove(self, ctx, *, text: str):
        '''
        Removes the given string from the server-wide filter. You don't need to
        tell it which filter level it was for.
        '''

        await self.delete_filter(ctx.message, ctx.guild, text)

    @filter_guild.command(name='flag', aliases=['warn', 'alert', 'notice'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_flag(self, ctx, *, text: str):
        '''
        Adds the text to the server-wide flagging filter. If a message
        with this content is found, staff is alerted in the configured
        channel.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        await self.add_filter(ctx.message, ctx.guild, FilterType.FLAG, text)

    @filter_guild.command(name='block', aliases=['deny', 'delete', 'del', 'remove'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_block(self, ctx, *, text: str):
        '''
        Adds the text to the server-wide blocking filter. If a message with
        this content is found, it is deleted and the contents of
        the message are sent to the user.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        await self.add_filter(ctx.message, ctx.guild, FilterType.BLOCK, text)

    @filter_guild.command(name='jail', aliases=['dunce', 'punish'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_jail(self, ctx, *, text: str):
        '''
        Adds the text to the server-wide jailing filter. If a message with
        this content is found, it is deleted and the user is given the configured
        jail role. The contents of their message is printed in jail channel, with
        a message about how that behavior is inappropriate.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        await self.add_filter(ctx.message, ctx.guild, FilterType.JAIL, text)

    @filter.group(name='channel', aliases=['chan', 'ch', 'c'])
    @commands.guild_only()
    async def filter_channel(self, ctx):
        '''
        Allows managing the server-wide filter.
        '''

        if ctx.subcommand_passed in ('chan', 'ch', 'c'):
            # TODO send help
            await ctx.message.add_reaction(Reactions.FAIL)

    @filter_channel.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def filter_channel_show(self, ctx):
        '''
        List all currently filtered words in the channel filter.
        '''

        await self.show_filter(ctx.message, ctx.author, ctx.guild.name, self.filters[ctx.guild])

    @filter_channel.command(name='flag', aliases=['warn', 'alert', 'notice'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_flag(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Adds the text to the channel flagging filter. If a message
        with this content is found, staff is alerted in the configured
        channel.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        await self.add_filter(ctx.message, channel, FilterType.FLAG, text)

    @filter_channel.command(name='block', aliases=['deny', 'delete', 'del', 'remove'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_block(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Adds the text to the channel blocking filter. If a message with
        this content is found, it is deleted and the contents of
        the message are sent to the user.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        await self.add_filter(ctx.message, channel, FilterType.BLOCK, text)

    @filter_channel.command(name='jail', aliases=['dunce', 'punish'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_jail(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Adds the text to the channel jailing filter. If a message with
        this content is found, it is deleted and the user is given the configured
        jail role. The contents of their message is printed in jail channel, with
        a message about how that behavior is inappropriate.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        await self.add_filter(ctx.message, channel, FilterType.JAIL, text)

    @filter_channel.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_remove(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Removes the given string from this channel's filter. You don't need to
        tell it which filter level it was for.
        '''

        await self.delete_filter(ctx.message, channel, text)
