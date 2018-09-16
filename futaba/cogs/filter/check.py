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
import re
from collections import namedtuple

import discord

from futaba.enums import FilterType, LocationType
from futaba.utils import Dummy, escape_backticks
from .download import download_attachments, download_links

logger = logging.getLogger(__name__)

__all__ = [
    'check_message',
    'check_message_edit',
]

JournalProperties = namedtuple('JournalProperties', ('verb', 'path', 'icon'))

JOURNAL_PROPERTIES = {
    FilterType.FLAG: JournalProperties(verb='Flagged', path='flag', icon='flag'),
    FilterType.BLOCK: JournalProperties(verb='Blocked', path='block', icon='deleted'),
    FilterType.JAIL: JournalProperties(verb='Jailed for', path='jail', icon='jail'),
}

URL_REGEX = re.compile(
    r'https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{2,256}\.[a-z]{2,6}\b([-a-zA-Z0-9@:%_\+.~#?&//=]*)'
)

def journal_violation(journal, message, filter_type, flagged_content):
    props = JOURNAL_PROPERTIES[filter_type]
    content = f'{props.verb} message content: `{flagged_content}` by {message.author.mention} in {message.channel.mention}'
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
        (LocationType.GUILD, cog.filters[message.guild]),
        (LocationType.CHANNEL, cog.filters[message.channel]),
    )

    for location_type, all_filters in filter_groups:
        for filter_text, (filter, filter_type) in all_filters.items():
            if filter.matches(content):
                await found_violation(
                    cog.journal,
                    message,
                    content,
                    location_type,
                    filter_type,
                    filter_text
                )
                return

    logger.debug("No violations found!")

async def check_file_filter(cog, message):
    file_urls = URL_REGEX.findall(message.content)

    # See if the message even has attachments
    if not message.attachments:
        logger.debug("Message has no attachments, skipping")
        return

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
    filter_settings = bot.sql.settings.get_filter_settings(message.guild)
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

async def found_violation(journal, message, content, location_type, filter_type, filter_text):
    '''
    Processes a violation of the text filter. This method is responsible
    for actual enforcement, based on the filter_type.
    '''

    logger.info("Punishing %s filter violation (%r, level %s) by '%s' (%d)",
            location_type.value, filter_text, filter_type.value, message.author.name, message.author.id)

    severity = filter_type.level
    jail_role = Dummy() # FIXME
    jail_role.name = 'Dunce Hat'

    # Escape content for display
    escaped_filter_text = escape_backticks(filter_text)
    escaped_content = escape_backticks(content)

    if len(escaped_content) > 1800:
        escaped_content = escaped_content[:1800] + ' ... (message too long)'

    async def message_violator():
        logger.debug("Sending message to user who violated the filter")
        lines = [
            f"The message you posted in {message.channel.mention} violates a {location_type.value} "
            f"{filter_type.value} filter disallowing `{escaped_filter_text}`."
        ]

        if severity >= FilterType.JAIL.level:
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

        embed = discord.Embed(description=content)
        embed.timestamp = discord.utils.snowflake_time(message.id)
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar_url)
        to_send = f"The content of the deleted message {embed_caveat} is:"
        await message.author.send(content=to_send, embed=embed)

        lines.extend((
            'or, quoted:',
            '```',
            escaped_content,
            '```',
            'Contact a moderator if you have questions.',
        ))

        await message.author.send(content='\n'.join(lines))

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
