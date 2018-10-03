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
from futaba.enums import FilterType, LocationType, NameType
from futaba.str_builder import StringBuilder
from futaba.utils import URL_REGEX, escape_backticks

logger = logging.getLogger(__name__)

__all__ = [
    'MASK_NICK',
    'check_message',
    'check_message_edit',
    'check_member_update',
]

# The nickname to apply to cover up an offensive username
MASK_NICK = 'XXX'

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

FoundNameViolation = namedtuple('FoundNameViolation', (
    'filter_type',
    'filter_text',
))

JournalProperties = namedtuple('JournalProperties', ('verb', 'path', 'icon'))

JOURNAL_PROPERTIES = {
    FilterType.FLAG: JournalProperties(verb='Flagged', path='flag', icon='flag'),
    FilterType.BLOCK: JournalProperties(verb='Blocked', path='block', icon='deleted'),
    FilterType.JAIL: JournalProperties(verb='Jailed for', path='jail', icon='jail'),
}

def journal_violation(journal, head, message, filter_type, flagged):
    props = JOURNAL_PROPERTIES[filter_type]
    user = message.author
    channel = message.channel
    content = f'{props.verb} message content: `{flagged}` by {user.mention} in {channel.mention}'
    journal.send(f'{head}/{props.path}', message.guild, content, icon=props.icon)

def journal_name_violation(journal, member, name_type, filter_type, flagged):
    props = JOURNAL_PROPERTIES[filter_type]
    content = f'{props.verb} {name_type.value}: `{flagged}` by {member.mention}'
    journal.send(f'{name_type.value}/{props.path}', member.guild, content, icon=props.icon)

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

def filter_immune(bot, guild, member, channel=None):
    '''
    Checks for certain people who are not subject to the filter's effects.
    '''

    # This is a boolean function with lots of ifs/returns for readability
    # pylint: disable=too-many-return-statements

    # Don't trigger on ourselves
    if member == bot:
        return True

    # Check if bots have filter immunity
    filter_settings = bot.sql.filter.get_settings(guild)
    if filter_settings.bot_immune:
        if member.bot:
            return True

    # Ignore owners
    if member.id in bot.config.owner_ids:
        return True

    # Check admins
    perms = channel.permissions_for(member)
    if channel is not None:
        if perms.manage_guild:
            return True

    # Check moderators (if enabled)
    if filter_settings.manage_messages_immune:
        if perms.manage_messages:
            return True

    # Check manually-added users
    if bot.sql.filter.user_is_filter_immune(guild, member):
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
        response = StringBuilder(
            f'The message you posted in {message.channel.mention} violates a {location_type.value} '
            f'{filter_type.value} filter disallowing `{escaped_filter_text}`.'
        )

        if severity >= FilterType.JAIL.level:
            if roles.jail is not None:
                response.writeln(
                    'This offense is serious enough to warrant immediate revocation of posting privileges.\n'
                    f'As such, you have been assigned the `{roles.jail.name}` role, until a moderator clears you.'
                )

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
        journal_violation(journal, 'text', message, filter_type, escaped_content)

    if severity >= FilterType.BLOCK.level:
        logger.info("Deleting inappropriate message id %d and notifying user", message.id)
        await asyncio.gather(
            message.delete(),
            message_violator(),
        )

    if severity >= FilterType.JAIL.level:
        if roles.jail is None:
            logger.info("Jailing user for inappropriate message, except there is no jail role configured!")
            content = f'Cannot jail {message.author.mention} for filter violation because no jail role is set!'
            journal.send('text/jail', message.guild, content, icon='warning')
        else:
            logger.info("Jailing user for inappropriate message")
            await message.author.add_roles(roles.jail, reason='Jailed for violating file filter')

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
            if roles.jail is not None:
                response.writeln(
                    'This offense is serious enough to warrant immediate revocation of posting privileges.\n'
                    f'As such, you have been assigned the `{roles.jail.name}` role, until a moderator clears you.'
                )

        kwargs = {}
        if reupload:
            response.writeln("In case the link is broken, the file has been attached below:")
            filename = os.path.basename(urlparse(url).path)
            kwargs['file'] = discord.File(binio.getbuffer(), filename=filename)

        kwargs['content'] = str(response)
        await message.author.send(**kwargs)

    if severity >= FilterType.FLAG.level:
        logger.info("Notifying staff of filter violation")
        journal_violation(journal, 'file', message, filter_type, url)

    if severity >= FilterType.BLOCK.level:
        logger.info("Deleting inappropriate message id %d and notifying user", message.id)
        await asyncio.gather(
            message.delete(),
            message_violator(),
        )

    if severity >= FilterType.JAIL.level:

        if roles.jail is None:
            logger.info("Jailing user for inappropriate file, except there is no jail role configured!")
            content = f'Cannot jail {message.author.mention} for filter violation because no jail role is set!'
            journal.send('file/jail', message.guild, content, icon='warning')
        else:
            logger.info("Jailing user for inappropriate file")
            await message.author.add_roles(roles.jail, reason='Jailed for violating file filter')

async def check_name_filter(cog, name, name_type, member):
    '''
    Checks the given name against all filters, and enforces with a dunce.
    '''

    logger.debug("Checking name: %r", name)

    # Iterate through all guild filters
    triggered = None

    for filter_text, (filter, filter_type) in cog.filters[member.guild].items():
        if filter.matches(name):
            if triggered is None or filter_type.value > triggered.filter_type.value:
                triggered = FoundNameViolation(
                    filter_type=filter_type,
                    filter_text=filter_text,
                )

    if triggered is None:
        logger.debug("No name violations found!")
        return

    filter_type = triggered.filter_type
    filter_text = triggered.filter_text
    escaped_name = escape_backticks(name)
    escaped_filter_text = escape_backticks(filter_text)

    logger.info("Punishing name filter violation (%r, level %s) by '%s' (%d)",
            filter_text, filter_type.value, member.name, member.id)

    roles = cog.bot.sql.settings.get_special_roles(member.guild)

    async def message_violator(jailed):
        response = StringBuilder(
            f'The {name_type.value} you just set violates a {filter_type.value} text filter '
            f'disallowing `{escaped_filter_text}`.\n'
        )

        if jailed:
            if roles.jail is not None:
                response.writeln(
                    f'In the mean time, you have been assigned the `{roles.jail.name}` role, '
                    'revoking your posting privileges until a moderator clears you.'
                )
        else:
            response.writeln(
                'Your name has been manually cleared. Please do not set your name to '
                'anything offensive in the future.'
            )

        await member.send(content=str(response))

    severity = filter_type.level
    jail_anyways = False

    if severity >= FilterType.FLAG.level:
        logger.info("Notifying staff of filter violation")
        journal_name_violation(cog.journal, member, name_type, filter_type, escaped_name)

    if severity >= FilterType.BLOCK.level:
        logger.info("Removing bad %s from member", name_type.value)
        if name_type == NameType.USER:
            jail_anyways = True
            await member.edit(
                nick=MASK_NICK,
                reason='Hid username for violating {filter_type.value} level name filter',
            )
        elif name_type == NameType.NICK:
            await member.edit(
                nick=None,
                reason=f'Removed nickname for violating {filter_type.value} level name filter',
            )
        else:
            raise ValueError(f"Unknown value for NameType: {name_type!r}")

    if severity >= FilterType.JAIL.level or jail_anyways:
        if roles.jail is None:
            logger.info("Jailing user for inappropriate name, except there is no jail role configured!")
            content = f'Cannot jail {member.mention} for name violation because no jail role is set!'
            cog.journal.send('name/jail', member.guild, content, icon='warning')
        else:
            logger.info("Jailing user for inappropriate name")
            await asyncio.gather(
                message_violator(jailed=True),
                member.add_roles(roles.jail, reason='Jailed for violating name filter')
            )

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
    if filter_immune(cog.bot, message.guild, message.author, message.channel):
        logger.debug("This user is immune to the filter")
        return

    logger.debug("Checking message id %d (by '%s' (%d)) for filter violations",
            message.id, message.author.name, message.author.id)

    await asyncio.gather(
        check_text_filter(cog, message),
        check_file_filter(cog, message),
    )

async def check_message_edit(cog, before, after):
    '''
    Checks the edited message against all applicable filters, and
    takes appropriate action if necessary.
    '''

    logger.debug("Checking message edit")
    await check_message(cog, after)

async def check_member_join(cog, member):
    '''
    Checks a new member against all text filters to ensure
    they don't have an inappropriate username or nickname.
    '''

    logger.debug("Checking member join")
    guild = member.guild

    # Check that we actually have permissions to manage roles
    if not guild.me.guild_permissions.manage_roles:
        logger.debug("I don't have permission to manage roles here")
        return

    # Check filter immunity
    if filter_immune(cog.bot, guild, member):
        logger.debug("This user is immune to the filter")
        return

    # Cannot be parallelized because we can only renick if the username is ok
    await check_name_filter(cog, member.name, NameType.USER, member)
    if member.nick is not None:
        await check_name_filter(cog, member.nick, NameType.NICK, member)

async def check_member_update(cog, before, after):
    '''
    Checks the member update against all text filters to ensure
    they didn't change their username or nickname to something
    inappropriate.
    '''

    logger.debug("Checking member update")
    guild = before.guild

    # Check that we actually have permissions to manage roles
    if not guild.me.guild_permissions.manage_roles:
        logger.debug("I don't have permission to manage roles here")
        return

    # Cannot be parallelized because we can only renick if the username is ok
    if before.name != after.name:
        await check_name_filter(cog, after.name, NameType.USER, after)

    if before.nick != after.nick and after.nick is not None:
        if after.nick == MASK_NICK:
            logger.debug("User has masked nickname, ignoring")
            return

        await check_name_filter(cog, after.nick, NameType.NICK, after)
