#
# cogs/filter/check.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
import os
from collections import namedtuple
from hashlib import sha1
from urllib.parse import urlparse

import discord

from futaba.download import download_links
from futaba.enums import FilterType, LocationType
from futaba.str_builder import StringBuilder
from futaba.utils import URL_REGEX, Dummy, escape_backticks

logger = logging.getLogger(__name__)

__all__ = [
    'check_message',
    'check_message_edit',
]

FoundTextViolation = namedtuple('FoundTextViolation', (
    'journal',
    'message',
    'content',
    'location_type',
    'filter_type',
    'filter_text'
))

FoundFileViolation = namedtuple('FoundFileViolation', (
    'journal',
    'message',
    'filter_type',
    'url',
    'binio',
    'hashsum',
))

JournalProperties = namedtuple('JournalProperties', ('verb', 'path', 'icon'))

JOURNAL_PROPERTIES = {
    FilterType.FLAG: JournalProperties(verb='Flagged', path='flag', icon='flag'),
    FilterType.BLOCK: JournalProperties(verb='Blocked', path='block', icon='deleted'),
    FilterType.JAIL: JournalProperties(verb='Jailed for', path='jail', icon='jail'),
}

def journal_violation(journal, message, filter_type, flagged):
    props = JOURNAL_PROPERTIES[filter_type]
    user = message.author
    channel = message.channel
    content = f'{props.verb} message content: `{flagged}` by {user.mention} in {channel.mention}'
    journal.send(props.path, message.guild, content, icon=props.icon)

async def check_message(cog, message):
    '''
    Checks the message against all applicable filters, and takes
    the appropriate action if necessary.
    '''

    # Don't filter PMs
    if message.guild is None:
        logger.debug("Not checking message because it's not from a guild")
        return

    # Check that we actually have permissions to delete
    if not message.channel.permissions_for(message.guild.me).manage_messages:
        logger.debug("I don't have permission to delete messages here")
        return

    # Check filter immunity
    if filter_immune(cog.bot, message):
        logger.debug("This user is immune to the filter")
        return

    logger.debug("Checking message id %d (by '%s' (%d)) for filter violations",
            message.id, message.author.name, message.author.id)

    await asyncio.gather(
        check_text_filter(cog, message),
        check_file_filter(cog, message),
    )

async def check_text_filter(cog, message):
    # Also check embed content
    content = StringBuilder(message.content)
    for embed in message.embeds:
        embed_dict = embed.to_dict()
        content.writeln(embed_dict.get('description', ''))
        content.writeln(embed_dict.get('title', ''))

        for field in embed_dict.get('fields', []):
            content.writeln(field.get('name', ''))
            content.writeln(field.get('value', ''))

    # This is the string we will validate against
    to_check = str(content)
    logger.debug("Content to check: %r", to_check)

    # Iterate through all guild filters
    triggered = None
    filter_groups = (
        (LocationType.GUILD, cog.filters[message.guild]),
        (LocationType.CHANNEL, cog.filters[message.channel]),
    )

    for location_type, all_filters in filter_groups:
        for filter_text, (filter, filter_type) in all_filters.items():
            if filter.matches(to_check):
                if triggered is None or filter_type.value > triggered.filter_type.value:
                    triggered = FoundTextViolation(
                        journal=cog.journal,
                        message=message,
                        content=to_check,
                        location_type=location_type,
                        filter_type=filter_type,
                        filter_text=filter_text,
                    )

    if triggered is None:
        logger.debug("No text violations found!")
    else:
        roles = cog.bot.sql.settings.get_special_roles(message.guild)
        await found_text_violation(triggered, roles)

async def check_file_filter(cog, message):
    file_urls = URL_REGEX.findall(message.content)
    file_urls.extend(attach.url for attach in message.attachments)

    if not file_urls:
        logger.debug("Message has no attachments, skipping")
        return

    triggered = None
    buffers = await download_links(file_urls)
    hashsums = {}

    for binio, url in zip(buffers, file_urls):
        if binio is not None:
            digest = sha1(binio.getbuffer()).digest()
            hashsums[digest] = (binio, url)

    for hashsum, filter_type in cog.content_filters[message.guild].items():
        try:
            binio, url = hashsums[hashsum]
        except KeyError:
            # Hash sum not found, not a match
            continue

        if triggered is None or filter_type.value > triggered.filter_type.value:
            triggered = FoundFileViolation(
                            journal=cog.journal,
                            message=message,
                            filter_type=filter_type,
                            url=url,
                            binio=binio,
                            hashsum=hashsum,
                        )

    if triggered is None:
        logger.debug("No content violations found!")
    else:
        roles = cog.bot.sql.settings.get_special_roles(message.guild)
        settings = cog.bot.sql.filter.get_settings(message.guild)
        await found_file_violation(triggered, roles, settings.reupload)

async def check_message_edit(cog, before, after):
    logger.debug("Checking message edit")
    await check_message(cog, after)

def filter_immune(bot, message):
    '''
    Checks for certain people who are not subject to the filter's effects.
    '''

    # This is a boolean function with lots of ifs/returns for readability
    # pylint: disable=too-many-return-statements

    # Don't trigger on ourselves
    if message.author == bot:
        return True

    # Check if bots have filter immunity
    filter_settings = bot.sql.filter.get_settings(message.guild)
    if filter_settings.bot_immune:
        if message.author.bot:
            return True

    # Ignore owners
    if message.author.id in bot.config.owner_ids:
        return True

    # Check admins
    perms = message.channel.permissions_for(message.author)
    if perms.manage_guild:
        return True

    # Check moderators (if enabled)
    if filter_settings.manage_messages_immune:
        if perms.manage_messages:
            return True

    # Check manually-added users
    if bot.sql.filter.user_is_filter_immune(message.guild, message.author):
        return True

    return False

async def found_text_violation(triggered, roles):
    '''
    Processes a violation of the text filter. This coroutine is responsible
    for actual enforcement, based on the filter_type.
    '''

    journal = triggered.journal
    message = triggered.message
    content = triggered.content
    location_type = triggered.location_type
    filter_type = triggered.filter_type
    filter_text = triggered.filter_text

    logger.info("Punishing %s filter violation (%r, level %s) by '%s' (%d)",
            location_type.value, filter_text, filter_type.value, message.author.name, message.author.id)

    severity = filter_type.level

    # Escape content for display
    escaped_filter_text = escape_backticks(filter_text)
    escaped_content = escape_backticks(content)

    if len(escaped_content) > 1800:
        escaped_content = escaped_content[:1800] + ' ... (message too long)'

    async def message_violator():
        logger.debug("Sending message to user who violated the filter")
        response = StringBuilder()
        response.write(
            f'The message you posted in {message.channel.mention} violates a {location_type.value} '
        )
        response.writeln(f'{filter_type.value} filter disallowing `{escaped_filter_text}`.')

        if severity >= FilterType.JAIL.level:
            response.writeln(
                "This offense is serious enough to warrant immediate revocation of posting privileges."
            )
            response.writeln(
                f"As such, you have been assigned the {roles.jail.mention} role, until a moderator clears you."
            )
            await message.author.add_roles(roles.jail, reason='Jailed for violating text filter')

        await message.author.send(content=str(response))
        response.clear()

        if message.content != content:
            embed_caveat = '(including text from all embeds attached to your message)'
        else:
            embed_caveat = ''

        embed = discord.Embed(description=content)
        embed.timestamp = discord.utils.snowflake_time(message.id)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
        to_send = f"The content of the deleted message {embed_caveat} is:"
        await message.author.send(content=to_send, embed=embed)

        response.writeln('or, quoted:')
        response.writeln('```')
        response.writeln(escaped_content)
        response.writeln('```')
        response.writeln('Contact a moderator if you have questions.')
        await message.author.send(content=str(response))

    if severity >= FilterType.FLAG.level:
        logger.info("Notifying staff of filter violation")
        journal_violation(journal, message, filter_type, escaped_content)

    if severity >= FilterType.BLOCK.level:
        logger.info("Deleting inappropriate message id %d and notifying user", message.id)
        await asyncio.gather(
            message.delete(),
            message_violator(),
        )

    if severity >= FilterType.JAIL.level:
        # TODO jail user
        # this requires the jailing/duncing mechanism to be complete
        # and having the dunce role available in settings
        logger.info("Jailing user for inappropriate message")

async def found_file_violation(roles, triggered, reupload):
    '''
    Processes a violation of the file content filter. This coroutine is responsible
    for actual enforcement, based on the filter_type.
    '''

    journal = triggered.journal
    message = triggered.message
    filter_type = triggered.filter_type
    url = triggered.url
    binio = triggered.binio
    hashsum = triggered.hashsum

    logger.info("Punishing file content filter violation (%s, level %s) by '%s' (%d)",
            hashsum.hex(), filter_type.value, message.author.name, message.author.id)

    severity = filter_type.level

    async def message_violator():
        logger.debug("Sending message to user who violated the filter")
        response = StringBuilder()
        response.write(
            f'The message you posted in {message.channel.mention} contains or links to a file '
        )
        response.writeln(f'that violates a {filter_type.value} content filter: `{hashsum.hex()}`.')
        response.writeln(f'Your original link: <{url}>')

        if reupload:
            response.writeln('The filtered file has been attached to this message.')

        if severity >= FilterType.JAIL.level:
            response.writeln(
                "This offense is serious enough to warrant immediate revocation of posting privileges."
            )
            response.writeln(
                f"As such, you have been assigned the `{roles.jail.name}` role, until a moderator clears you."
            )
            await message.author.add_roles(roles.jail, reason='Jailed for violating file filter')

        kwargs = {}
        if reupload:
            response.writeln("In case the link is broken, the file has been attached below:")
            filename = os.path.basename(urlparse(url).path)
            kwargs['file'] = discord.File(binio.getbuffer(), filename=filename)

        kwargs['content'] = str(response)
        await message.author.send(**kwargs)

    if severity >= FilterType.FLAG.level:
        logger.info("Notifying staff of filter violation")
        journal_violation(journal, message, filter_type, url)

    if severity >= FilterType.BLOCK.level:
        logger.info("Deleting inappropriate message id %d and notifying user", message.id)
        await asyncio.gather(
            message.delete(),
            message_violator(),
        )

    if severity >= FilterType.JAIL.level:
        # TODO jail user
        # this requires the jailing/duncing mechanism to be complete
        # and having the dunce role available in settings
        logger.info("Jailing user for inappropriate attachment")
