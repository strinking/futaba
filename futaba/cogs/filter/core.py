#
# cogs/filter/core.py
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
Cog to handle text filtering, including both hard and soft enforcement,
similar unicode characters, and stripping unicode whitespace.
'''

import asyncio
import logging
from collections import defaultdict

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import FilterType, Reactions
from futaba.exceptions import SendHelp
from futaba.utils import async_partial, escape_backticks
from .check import check_message, check_message_edit
from .filter import Filter
from .manage import add_filter, delete_filter, show_filter
from .manage import check_hashsums, add_content_filter, delete_content_filter, show_content_filter

logger = logging.getLogger(__name__)

__all__ = [
    'Filtering',
]

class Filtering:
    __slots__ = (
        'bot',
        'journal',
        'filters',
        'content_filters',
        'check_message',
        'check_message_edit',
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/filter')
        self.filters = defaultdict(dict)
        self.content_filters = defaultdict(dict)
        self.check_message = async_partial(check_message, self)
        self.check_message_edit = async_partial(check_message_edit, self)

        logger.info("Fetching previously stored filters")
        sql = self.bot.sql.filter
        for guild in self.bot.guilds:
            # Get filter settings
            sql.fetch_settings(guild)

            # Guild text filters
            for text, filter_type in sql.get_filters(guild).items():
                self.filters[guild][text] = (Filter(text), filter_type)

            # Channel text filters
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    for text, filter_type in sql.get_filters(channel).items():
                        self.filters[channel][text] = (Filter(text), filter_type)

            # Guild content filters
            for hashsum, (filter_type, description) in sql.get_content_filters(guild).items():
                self.content_filters[guild][hashsum] = (filter_type, description)

    def __unload(self):
        '''
        Remove listeners when unloading the cog.
        '''

        self.bot.remove_listener(self.check_message, 'on_message')
        self.bot.remove_listener(self.check_message_edit, 'on_message_edit')

    @commands.group(name='filter')
    @commands.guild_only()
    async def filter(self, ctx):
        '''
        Adds, removes, or lists words in the text filter.
        It ignores case and checks for unicode strings that look similar.
        '''

        if ctx.invoked_subcommand is None:
            raise SendHelp(ctx.command)

    @commands.group(name='ffilter', aliases=['filefilter', 'content', 'cfilter'])
    @commands.guild_only()
    async def ffilter(self, ctx):
        '''
        Adds, removes, or lists SHA1 hashes in the content filter.
        '''

        if ctx.invoked_subcommand is None:
            raise SendHelp(ctx.command)

    @ffilter.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def ffilter_show(self, ctx):
        '''
        List all currently filtered SHA1 file hashes in the guild's filter.
        '''

        await show_content_filter(self.content_filters[ctx.guild], ctx.message)

    @ffilter.command(name='flag', aliases=['warn', 'alert', 'notice'])
    @commands.guild_only()
    @permissions.check_mod()
    async def ffilter_flag(self, ctx, hashsum: str, description: str):
        '''
        Adds the given SHA1 hashes to the guild's flagging filter, which notifies staff when posted.
        It does not notify the user or delete the message.

        You must specify a description of the file being filtered.
        '''

        await check_hashsums((hashsum,), ctx.message)
        content = f'Added content flag filter for `{hashsum}`'
        self.journal.send('content/new/flag', ctx.guild, content, icon='filter',
                hashsum=hashsum, description=description, cause=ctx.author)
        await add_content_filter(
            self.bot,
            self.content_filters,
            ctx.message,
            FilterType.FLAG,
            hashsum,
            description,
        )

    @ffilter.command(name='block', aliases=['deny', 'autoremove'])
    @commands.guild_only()
    @permissions.check_mod()
    async def ffilter_block(self, ctx, hashsum: str, description: str):
        '''
        Adds the given SHA1 hashes to the guild's blocking filter, automatically deleting any messages.
        It does not notify the user or delete the message.

        You must specify a description of the file being filtered.
        '''

        await check_hashsums((hashsum,), ctx.message)
        content = f'Added content block filter for `{hashsum}`'
        self.journal.send('content/new/block', ctx.guild, content, icon='filter')
        await add_content_filter(
            self.bot,
            self.content_filters,
            ctx.message,
            FilterType.BLOCK,
            hashsum,
            description,
        )

    @ffilter.command(name='jail', aliases=['dunce', 'punish', 'mute'])
    @commands.guild_only()
    @permissions.check_mod()
    async def ffilter_jail(self, ctx, hashsum: str, description: str):
        '''
        Adds the given SHA1 hashes to the guild's jailing filter, which will automatically jail users.
        Like the blocking filter, it will also delete the message and send the user a warning.

        You must specify a description of the file being filtered.
        '''

        await check_hashsums((hashsum,), ctx.message)
        content = f'Added content jail filter for `{hashsum}`'
        self.journal.send('content/new/jail', ctx.guild, content, icon='filter')
        await add_content_filter(
            self.bot,
            self.content_filters,
            ctx.message,
            FilterType.JAIL,
            hashsum,
            description,
        )

    @ffilter.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_mod()
    async def ffilter_remove(self, ctx, *hashsums: str):
        '''
        Removes the given SHA1 hashes from the guild filter.
        You don't need to specify which filter level they were for.
        '''

        await check_hashsums(hashsums, ctx.message)
        str_hashsums = ' '.join(f'`{hashsum}`' for hashsum in hashsums)
        content = f'Removed content jail filter for {str_hashsums}'
        self.journal.send('content/remove', ctx.guild, content, icon='filter', hashsums=hashsums)
        await delete_content_filter(self.bot, self.content_filters, ctx.message, hashsums)

    @filter.group(name='immune', aliases=['imm', 'ignore', 'ign'])
    @commands.guild_only()
    async def filter_immunity(self, ctx):
        '''
        Maintaining the list of special user immunities to the filter.
        '''

        if ctx.subcommand_passed in ('immune', 'imm', 'ignore', 'ign'):
            raise SendHelp(ctx.command)

    @filter_immunity.command(name='add', aliases=['append', 'extend', 'new'])
    @commands.guild_only()
    @permissions.check_admin()
    async def filter_immunity_add(self, ctx, *members: discord.Member):
        '''
        Adds a set of users to the server filter immunity list.
        '''

        if not members:
            await Reactions.FAIL.add(ctx.message)
            return

        member_names = ', '.join((f"'{member.name}' ({member.id})" for member in members))
        logger.info("Adding members to guild '%s' (%d) filter immunity list: %s",
                ctx.guild.name, ctx.guild.id, member_names)

        with self.bot.sql.transaction():
            for member in members:
                logger.debug("Adding member: %s (%d)", member.display_name, member.id)
                self.bot.sql.filter.add_filter_immune_user(ctx.guild, member)

        for member in members:
            content = f'Added {member.name}#{member.discriminator} to filter immunity list'
            self.journal.send('immunity/new', ctx.guild, content, icon='person',
                    member=member, cause=ctx.author)

        await Reactions.SUCCESS.add(ctx.message)

    @filter_immunity.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_admin()
    async def filter_immunity_remove(self, ctx, *members: discord.Member):
        '''
        Removes a set of users from the server filter immunity list.
        '''

        if not members:
            await Reactions.FAIL.add(ctx.message)
            return

        member_names = ', '.join((f"'{member.name}' ({member.id})" for member in members))
        logger.info("Removing members to guild '%s' (%d) filter immunity list: %s",
                ctx.guild.name, ctx.guild.id, member_names)

        with self.bot.sql.transaction():
            for member in members:
                logger.debug("Removing member: %s (%d)", member.display_name, member.id)
                self.bot.sql.filter.remove_filter_immune_user(ctx.guild, member)

        for member in members:
            content = f'Removed {member.name}#{member.discriminator} from filter immunity list'
            self.journal.send('immunity/remove', ctx.guild, content, icon='person')

        await Reactions.SUCCESS.add(ctx.message)

    @filter_immunity.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def filter_immunity_show(self, ctx):
        '''
        Lists all users in this server's filter immunity list.
        '''

        user_ids = self.bot.sql.filter.get_filter_immune_users(ctx.guild)

        if user_ids:
            embed = discord.Embed(description='\n'.join(f'- <@{user_id}>' for user_id in user_ids))
            embed.set_author(name='Members with special filter immunity')
        else:
            embed = discord.Embed()
            embed.set_author(name='No members with special filter immunity')

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @filter.group(name='server', aliases=['srv', 's', 'guild', 'g'])
    @commands.guild_only()
    async def filter_guild(self, ctx):
        '''
        Allows managing the server-wide filter.
        '''

        if ctx.subcommand_passed in ('server', 'srv', 's', 'guild', 'g'):
            raise SendHelp(ctx.command)

    @filter_guild.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def filter_guild_show(self, ctx):
        '''
        List all currently filtered words in the server filter.
        '''

        await show_filter(self.filters[ctx.guild], ctx.message, ctx.author, ctx.guild.name)

    @filter_guild.command(name='flag', aliases=['warn', 'alert', 'notice'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_flag(self, ctx, *, text: str):
        '''
        Adds the text to the server-wide flagging filter, which notifies staff when posted.
        It does not notify the user or delete the message.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        content = f'Added guild flag filter for `{escape_backticks(text)}`'
        self.journal.send('guild/new/flag', ctx.guild, content, icon='filter',
                text=text, cause=ctx.author)
        await add_filter(self.bot, self.filters, ctx.message, ctx.guild, FilterType.FLAG, text)

    @filter_guild.command(name='block', aliases=['deny', 'autoremove'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_block(self, ctx, *, text: str):
        '''
        Adds the text to the server-wide blocking filter, automatically deleting any matching messages.
        A warning and the contents of the message are sent to the user who posted it.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        content = f'Added guild block filter for `{escape_backticks(text)}`'
        self.journal.send('guild/new/block', ctx.guild, content, icon='filter')
        await add_filter(self.bot, self.filters, ctx.message, ctx.guild, FilterType.BLOCK, text)

    @filter_guild.command(name='jail', aliases=['dunce', 'punish', 'mute'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_jail(self, ctx, *, text: str):
        '''
        Adds the text to the server-wide jailing filter, which will automatically jail users.
        Like the blocking filter, it will also delete the message and send the user a warning.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        content = f'Added guild jail filter for `{escape_backticks(text)}`'
        self.journal.send('guild/new/jail', ctx.guild, content, icon='filter')
        await add_filter(self.bot, self.filters, ctx.message, ctx.guild, FilterType.JAIL, text)

    @filter_guild.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_guild_remove(self, ctx, *, text: str):
        '''
        Removes the given string from the server-wide filter.
        You don't need to specify which filter level it was for.
        '''

        content = f'Removed guild filter for `{escape_backticks(text)}`'
        self.journal.send('guild/remove', ctx.guild, content, icon='filter',
                text=text, cause=ctx.author)
        await delete_filter(self.bot, self.filters, ctx.message, ctx.guild, text)

    @filter.group(name='channel', aliases=['chan', 'ch', 'c'])
    @commands.guild_only()
    async def filter_channel(self, ctx):
        '''
        Allows managing the local channel filter.
        '''

        if ctx.subcommand_passed in ('chan', 'ch', 'c'):
            raise SendHelp(ctx.command)

    @filter_channel.command(name='show', aliases=['display', 'list'])
    @commands.guild_only()
    async def filter_channel_show(self, ctx, channel: discord.TextChannel):
        '''
        List all currently filtered words in the channel filter.
        '''

        await show_filter(self.filters[channel], ctx.message, ctx.author, channel.mention)

    @filter_channel.command(name='flag', aliases=['warn', 'alert', 'notice'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_flag(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Adds the text to the channel's flagging filter, which notifies staff when posted.
        It does not notify the user or delete the message.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        content = f'Added channel flag filter in {channel.mention} for `{escape_backticks(text)}`'
        self.journal.send('channel/new/flag', ctx.guild, content, icon='filter',
                text=text, channel=channel, cause=ctx.author)
        await add_filter(self.bot, self.filters, ctx.message, channel, FilterType.FLAG, text)

    @filter_channel.command(name='block', aliases=['deny', 'autoremove'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_block(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Adds the text to the channel's blocking filter, automatically deleting any matching messages.
        A warning and the contents of the message are sent to the user who posted it.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        content = f'Added channel block filter in {channel.mention} for `{escape_backticks(text)}`'
        self.journal.send('channel/new/block', ctx.guild, content, icon='filter',
                text=text, channel=channel, cause=ctx.author)
        await add_filter(self.bot, self.filters, ctx.message, channel, FilterType.BLOCK, text)

    @filter_channel.command(name='jail', aliases=['dunce', 'punish', 'mute'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_jail(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Adds the text to the channel jailing filter, which will automatically jail users.
        Like the blocking filter, it will also delete the message and send the user a warning.

        The entire argument, complete with spaces and quotes, is interpreted as
        a single word to add to the filter.
        '''

        content = f'Added channel jail filter in {channel.mention} for `{escape_backticks(text)}`'
        self.journal.send('channel/new/jail', ctx.guild, content, icon='filter',
                text=text, channel=channel, cause=ctx.author)
        await add_filter(self.bot, self.filters, ctx.message, channel, FilterType.JAIL, text)

    @filter_channel.command(name='remove', aliases=['rm', 'delete', 'del'])
    @commands.guild_only()
    @permissions.check_mod()
    async def filter_channel_remove(self, ctx, channel: discord.TextChannel, *, text: str):
        '''
        Removes the given string from this channel's filter. You don't need to
        tell it which filter level it was for.
        '''

        content = f'Removed channel filter in {channel.mention} for `{escape_backticks(text)}`'
        self.journal.send('channel/remove', ctx.guild, content, icon='filter',
                text=text, channel=channel, cause=ctx.author)
        await delete_filter(self.bot, self.filters, ctx.message, channel, text)
