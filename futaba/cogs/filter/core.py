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
from futaba.enums import FilterType, LocationType, Reactions
from futaba.utils import Dummy
from .filter import Filter

logger = logging.getLogger(__name__)

__all__ = [
    'Filtering',
]

class Filtering:
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
            await Reactions.FAIL.add(message)
        else:
            self.filters[location][level].add(Filter(text))
            await Reactions.SUCCESS.add(message)

    async def delete_filter(self, message, location, text):
        logger.info("Removing %r from server filter for '%s' (%d)", text, location.name, location.id)

        with self.bot.sql.transaction():
            try:
                if self.bot.sql.filter.delete_filter(location, text):
                    logger.debug("Succesfully removed filter")
                    await Reactions.SUCCESS.add(message)
                else:
                    logger.debug("Filter was not present, deletion failed")
                    await Reactions.FAIL.add(message)
            except:
                logger.error("Error deleting filter", exc_info=1)
                await Reactions.FAIL.add(message)

    async def show_filter(self, message, author, location_name, all_filters):
        if all_filters:
            contents = []
            lines = [f'Filtered strings for {location_name}:']

            for filter_type, filters in all_filters.items():
                lines.extend((
                    f'{filter_type.emoji} {filter_type.description} {filter_type.emoji}',
                    '```',
                ))
                current_len = sum(len(line) + 1 for line in lines)

                if not filters:
                    lines.append('(none)')

                for filter in filters:
                    line = f'- "{filter.text}" {filter.text!r}'
                    current_len += len(line)

                    if current_len > 1900:
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
            Reactions.SUCCESS.add(message),
        )

    def filter_immune(self, message):
        '''
        Checks for certain people who are not subject to the filter's effects.
        '''

        # Don't trigger on ourselves
        if message.author == self.bot:
            return True

        # Check if bots have filter immunity
        filter_settings = self.bot.sql.settings.get_filter_settings(message.guild)
        if filter_settings.bot_immune:
            if message.author.bot:
                return True

        # Ignore owners
        if message.author.id in self.bot.config.owner_ids:
            return True

        # Check admins
        perms = message.channel.permissions_for(message.author)
        if perms.manage_guild:
            return True

        # Check moderators (if enabled)
        if filter_settings.manage_messages_immune:
            if perms.manage_messages:
                return True

        return False

    async def found_violation(self, message, content, location_type, filter_type, filter_text):
        '''
        Processes a violation of the text filter. This method is responsible
        for actual enforcement, based on the filter_type.
        '''

        logger.info("Punishing %s filter violation (%r, level %s) by '%s' (%d)",
                location_type.value, filter_text, filter_type.value, message.author.name, message.author.id)

        severity = filter_type.level
        jail_role = Dummy() # FIXME
        jail_role.name = 'Dunce Hat'

        async def message_violator():
            lines = [
                f"This message you posted in {message.channel.mention} violates a "
                "{filter_type.value} filter disallowing '{filter_text}' to appear in messages."
            ]

            if severity > FilterType.JAIL.level:
                lines.extend((
                    "This offense is serious enough to warrant immediate revocation of speaking privileges.",
                    f"As such, you have been assigned the `{jail_role.name}` role, until a moderator clears you.",
                ))

            await message.author.send(content='\n'.join(lines))
            lines.clear()

            if message.content != content:
                embed_caveat = '(including text from any embeds attached to your message)'
            else:
                embed_caveat = ''

            await message.author.send(content=f"The content of the deleted message {embed_caveat} is:")
            await message.author.send(content=content)

            lines.extend((
                'quoted version:',
                '```',
                content.replace('`', '\N{ARMENIAN COMMA}'),
                '```',
            ))

            await message.author.send(content='\n'.join(lines))

        if severity > FilterType.FLAG.level:
            # TODO notify staff
            # this requires the logging cog to be complete
            logger.info("Notifying staff of filter violation")

        if severity > FilterType.BLOCK.level:
            logger.info("Deleting inappropriate message id %d and notifying user", message.id)
            await asyncio.gather(
                message.delete(),
                message_violator(),
            )

        if severity > FilterType.JAIL.level:
            # TODO jail user
            # this requires the jailing/duncing mechanism to be complete
            # and having the dunce role available in settings
            logger.info("Jailing user for inappropriate message")

    async def check_message(self, message):
        '''
        Checks the message against all applicable filters, and takes
        the appropriate action if necessary.
        '''

        # Don't filter PMs
        if message.guild is None:
            return

        # Check that we actually have permissions to delete
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        # Check filter immunity
        if self.filter_immune(message):
            return

        logger.debug("Checking message id %d (by '%s' (%d)) for filter violations",
                message.id, message.author.name, message.author.id)

        # Also check embed content
        parts = [message.content]
        for embed in message.embeds:
            embed_dict = embed.to_dict()
            parts.append(embed_dict.get('description', ''))
            parts.append(embed_dict.get('title', ''))

            for field in embed_dict.get('fields', []):
                parts.append(field.get('name', ''))
                parts.append(field.get('value', ''))

        # This is the string we will validate against
        content = '\n'.join(parts)
        logger.debug("Content to check: %r", content)

        # Iterate through all guild filters
        filter_groups = (
            (LocationType.GUILD, self.filters[message.guild]),
            (LocationType.CHANNEL, self.filters[message.channel]),
        )

        for location_type, all_filters in filter_groups:
            for filter_type, filters in all_filters.items():
                for filter in filters:
                    if filter.matches(content):
                        await self.found_violation(
                            message,
                            content,
                            location_type,
                            filter_type,
                            filter.text
                        )

                        return

        logger.debug("No violations found!")

    async def check_message_edit(self, before, after):
        logger.debug("Checking message edit")
        await self.check_message(after)

    @commands.group(name='filter')
    @commands.guild_only()
    async def filter(self, ctx):
        '''
        Adds, removes, or lists words in the text filter.
        It ignores case and checks for unicode strings that look similar.
        '''

        if ctx.invoked_subcommand is None:
            # TODO send help
            await Reactions.FAIL.add(ctx.message)

    @commands.group(name='cfilter', aliases=['content', 'filefilter', 'ffilter'])
    @commands.guild_only()
    async def content(self, ctx):
        '''
        Adds, removes, or lists SHA512 hashes in the content filter.
        '''

        if ctx.invoked_subcommand is None:
            # TODO send help
            await Reactions.FAIL.add(ctx.message)

    @filter.group(name='server', aliases=['srv', 's', 'guild', 'g'])
    @commands.guild_only()
    async def filter_guild(self, ctx):
        '''
        Allows managing the server-wide filter.
        '''

        if ctx.subcommand_passed in ('server', 'srv', 's', 'guild', 'g'):
            # TODO send help
            await Reactions.FAIL.add(ctx.message)

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

    @filter_guild.command(name='block', aliases=['deny', 'autoremove'])
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
            await Reactions.FAIL.add(ctx.message)

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

    @filter_channel.command(name='block', aliases=['deny', 'autoremove'])
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
