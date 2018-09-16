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
from collections import defaultdict

from futaba.enums import FilterType, Reactions
from futaba.utils import READABLE_CHAR_SET, chunks, unicode_repr
from .filter import Filter

'''
Helper module to do the management of adding and removing filters.
Shared among multiple commands.
'''

logger = logging.getLogger(__name__)

__all__ = [
    'add_filter',
    'delete_filter',
    'show_filter',
    'show_content_filter',
]


async def add_filter(bot, filters, message, location, level, text):
    logger.info("Adding %r to server filter '%s' for '%s' (%d)",
            text, level, location.name, location.id)

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
    logger.info("Removing %r from server filter for '%s' (%d)", text, location.name, location.id)

    with bot.sql.transaction():
        try:
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
        lines = [f'**Filtered strings for {location_name}:**']
        filters = defaultdict(list)

        for filter_text, (_, filter_type) in all_filters.items():
            filters[filter_type].append(filter_text)

        for filter_type, filter_texts in filters.items():
            lines.extend((
                f'{filter_type.emoji} {filter_type.description} {filter_type.emoji}',
                '```',
            ))
            current_len = sum(len(line) + 1 for line in lines)

            if not filter_texts:
                lines.append('(none)')

            for filter_text in filter_texts:
                if all(ch in READABLE_CHAR_SET for ch in filter_text):
                    line = f'- "{filter_text}"'
                else:
                    line = f'- {unicode_repr(filter_text)} ["{filter_text}"]'

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
        contents = [f'**No filtered strings for {location_name}**']

    async def post_all():
        for content in contents:
            await author.send(content=content)

    await asyncio.gather(
        post_all(),
        Reactions.SUCCESS.add(message),
    )

async def show_content_filter(all_filters, message):
    if all_filters:
        contents = []
        lines = [f'**Filtered SHA512 hashes for {message.guild.name}:**']

        for filter_type in FilterType:
            lines.extend((
                f'{filter_type.emoji} {filter_type.description} {filter_type.emoji}',
                '```',
            ))

            hashsums = sorted(all_filters[filter_type])

            if not hashsums:
                lines.append('(none)')

            for chunked in chunks(hashsums, 140):
                for hashsum in chunked:
                    if hashsum is None:
                        break

                    lines.append(hashsum)
                lines.append('```')
                contents.append('\n'.join(lines))
                lines.clear()
                lines.append('```')
    else:
        contents = [f'**No filtered SHA512 hashes for {message.guild.name}**']

    async def post_all():
        for content in contents:
            await message.author.send(content=content)

    await asyncio.gather(
        post_all(),
        Reactions.SUCCESS.add(message),
    )
