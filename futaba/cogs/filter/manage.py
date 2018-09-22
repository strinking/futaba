#
# cogs/filter/manage.py
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
from collections import defaultdict

from futaba.enums import FilterType, Reactions
from futaba.str_builder import StringBuilder
from futaba.unicode import READABLE_CHAR_SET, unicode_repr
from .filter import Filter

HEXADECIMAL_REGEX = re.compile(r'[A-Fa-f0-9]+')

'''
Helper module to do the management of adding and removing filters.
Shared among multiple commands.
'''

logger = logging.getLogger(__name__)

__all__ = [
    'add_filter',
    'delete_filter',
    'show_filter',
    'add_content_filter',
    'delete_content_filter',
    'show_content_filter',
]


async def add_filter(bot, filters, message, location, level, text):
    logger.info("Adding %r to server filter '%s' for '%s' (%d)",
            text, level.value, location.name, location.id)

    try:
        with bot.sql.transaction():
            if text in filters[location]:
                bot.sql.filter.update_filter(location, level, text)
            else:
                bot.sql.filter.add_filter(location, level, text)
    except Exception as error:
        logger.error("Error adding filter", exc_info=error)
        await Reactions.FAIL.add(message)
    else:
        filters[location][text] = (Filter(text), level)
        await Reactions.SUCCESS.add(message)

async def delete_filter(bot, filters, message, location, text):
    logger.info("Removing %r from server filter for '%s' (%d)",
            text, location.name, location.id)

    try:
        with bot.sql.transaction():
            if bot.sql.filter.delete_filter(location, text):
                filters[location].pop(text, None)
                logger.debug("Succesfully removed filter")
                await Reactions.SUCCESS.add(message)
            else:
                logger.debug("Filter was not present, deletion failed")
                await Reactions.FAIL.add(message)
    except Exception as error:
        logger.error("Error deleting filter", exc_info=error)
        await Reactions.FAIL.add(message)

async def show_filter(all_filters, message, author, location_name):
    if all_filters:
        contents = []
        content = StringBuilder(f'**Filtered strings for {location_name}:**\n')
        filters = defaultdict(list)

        for filter_text, (_, filter_type) in all_filters.items():
            filters[filter_type].append(filter_text)

        for filter_type, filter_texts in filters.items():
            content.writeln(f'{filter_type.emoji} {filter_type.description} strings {filter_type.emoji}')
            content.writeln('```')

            if not filter_texts:
                content.writeln('(none)')
                continue

            for filter_text in filter_texts:
                if all(ch in READABLE_CHAR_SET for ch in filter_text):
                    content.writeln(f'- "{filter_text}"')
                else:
                    content.writeln(f'- {unicode_repr(filter_text)} ["{filter_text}"]')

                if len(content) > 1900:
                    # Too long, break into new message
                    content.writeln('```')
                    contents.append(str(content))

                    # Start buffer over
                    content.clear()
                    content.writeln('```')

            content.writeln('```')
        contents.append(str(content))
        content.clear()
    else:
        contents = [f'**No filtered strings for {location_name}**']

    async def post_all():
        for content in contents:
            await author.send(content=content)

    await asyncio.gather(
        post_all(),
        Reactions.SUCCESS.add(message),
    )

async def check_hashsums(hashsums, message):
    if not hashsums:
        await Reactions.FAIL.add(message)
    elif not all(map(lambda h: len(h) == 40 and HEXADECIMAL_REGEX.match(h), hashsums)):
        await asyncio.gather(
            message.channel.send(content='SHA1 hashes are 40 hex digits long.'),
            Reactions.FAIL.add(message),
        )

async def add_content_filter(bot, filters, message, level, hexsum, description):
    logger.info("Adding SHA1 to guild content filter '%s': %s", level.value, hexsum)

    try:
        hashsum = bytes.fromhex(hexsum)
        with bot.sql.transaction():
            if hashsum in filters[message.guild]:
                logger.debug("Updating existing content filter")
                bot.sql.filter.update_content_filter(message.guild, level, hashsum, description)
            else:
                logger.debug("Adding new content filter")
                bot.sql.filter.add_content_filter(message.guild, level, hashsum, description)

        filters[message.guild][hashsum] = (level, description)
    except Exception as error:
        logger.error("Error adding content filter", exc_info=error)
        await Reactions.FAIL.add(message)
    else:
        await Reactions.SUCCESS.add(message)

async def delete_content_filter(bot, filters, message, hexsums):
    logger.info("Removing SHA1s from guild content filter: %s", f'[", ".join(hexsums)]')

    try:
        hashsums = [bytes.fromhex(hexsum) for hexsum in hexsums]
        with bot.sql.transaction():
            for hashsum in hashsums:
                if hashsum in filters[message.guild]:
                    bot.sql.filter.delete_filter(message.guild, hashsum)
                    filters[message.guild].pop(hashsum, None)
                    logger.debug("Succesfully removed hashsum from filter")
                else:
                    logger.debug("Filter was not present, not deleting")
    except Exception as error:
        logger.error("Error deleting filter(s)", exc_info=error)
        success = False
        await Reactions.FAIL.add(message)
    else:
        await Reactions.SUCCESS.add(message)

async def show_content_filter(all_filters, message):
    if all_filters:
        contents = []
        lines = [f'**Filtered SHA1 hashes for {message.guild.name}:**']

        # Set up filter list
        print(f'all_filters: {all_filters}')
        filters = {filter_type: [] for filter_type in FilterType}
        for hashsum, (filter_type, description) in all_filters.items():
            filters[filter_type].append((hashsum.hex(), description))

        # Iterate through filters
        for filter_type in FilterType:
            filter_list = filters[filter_type]
            filter_list.sort()

            lines.extend((
                f'{filter_type.emoji} {filter_type.description} hashes {filter_type.emoji}',
                '```',
            ))

            if not filter_list:
                lines.extend((
                    '(none)',
                    '```',
                ))
                continue

            for hexsum, description in filter_list:
                lines.append(f'{hexsum} {description}')

                # Since we know the size of each hexsum, we know how many
                # we can fit in a message
                if len(lines) > 45:
                    lines.append('```')
                    contents.append('\n'.join(lines))
                    lines.clear()
                    lines.append('```')

            if len(lines) > 1:
                lines.append('```')
            else:
                lines.clear()

        if lines:
            contents.append('\n'.join(lines))
    else:
        contents = (f'**No filtered SHA1 hashes for {message.guild.name}**',)

    async def post_all():
        for content in contents:
            await message.author.send(content=content)

    await asyncio.gather(
        post_all(),
        Reactions.SUCCESS.add(message),
    )
