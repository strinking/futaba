#
# cogs/filter/manage.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging
import re
from collections import defaultdict

import discord

from futaba.enums import FilterType
from futaba.exceptions import CommandFailed
from futaba.str_builder import StringBuilder
from futaba.unicode import READABLE_CHAR_SET, unicode_repr
from .check import check_all_members_on_filter
from .filter import Filter

HEXADECIMAL_REGEX = re.compile(r"[A-Fa-f0-9]+")

"""
Helper module to do the management of adding and removing filters.
Shared among multiple commands.
"""

logger = logging.getLogger(__name__)

__all__ = [
    "add_filter",
    "delete_filter",
    "show_filter",
    "add_content_filter",
    "delete_content_filter",
    "show_content_filter",
]


async def add_filter(cog, filters, location, level, text):
    logger.info(
        "Adding %r to server filter '%s' for '%s' (%d)",
        text,
        level.value,
        location.name,
        location.id,
    )

    try:
        with cog.bot.sql.transaction():
            if text in filters[location]:
                cog.bot.sql.filter.update_filter(location, level, text)
            else:
                cog.bot.sql.filter.add_filter(location, level, text)
    except Exception as error:
        logger.error("Error adding filter", exc_info=error)
        raise CommandFailed()
    else:
        filter = Filter(text)
        filters[location][text] = (filter, level)

    if isinstance(location, discord.Guild):
        logger.debug("Checking all members against new guild text filter")
        cog.bot.loop.create_task(check_all_members_on_filter(cog, location, filter))


async def delete_filter(bot, filters, location, text):
    logger.info(
        "Removing %r from server filter for '%s' (%d)", text, location.name, location.id
    )

    try:
        with bot.sql.transaction():
            if bot.sql.filter.delete_filter(location, text):
                filters[location].pop(text, None)
                logger.debug("Succesfully removed filter")
            else:
                logger.debug("Filter was not present, deletion failed")
                raise CommandFailed()
    except Exception as error:
        logger.error("Error deleting filter", exc_info=error)
        raise CommandFailed()


async def show_filter(all_filters, author, location_name):
    if all_filters:
        contents = []
        content = StringBuilder(f"**Filtered strings for {location_name}:**\n")
        filters = defaultdict(list)

        for filter_text, (_, filter_type) in all_filters.items():
            filters[filter_type].append(filter_text)

        for filter_type, filter_texts in filters.items():
            content.writeln(
                f"{filter_type.emoji} {filter_type.description} strings {filter_type.emoji}"
            )
            content.writeln("```")

            if not filter_texts:
                content.writeln("(none)")
                continue

            for filter_text in filter_texts:
                if all(ch in READABLE_CHAR_SET for ch in filter_text):
                    content.writeln(f'- "{filter_text}"')
                else:
                    content.writeln(f'- {unicode_repr(filter_text)} ["{filter_text}"]')

                if len(content) > 1900:
                    # Too long, break into new message
                    content.writeln("```")
                    contents.append(str(content))

                    # Start buffer over
                    content.clear()
                    content.writeln("```")

            content.writeln("```")
        contents.append(str(content))
        content.clear()
    else:
        contents = [f"**No filtered strings for {location_name}**"]

    for content in contents:
        await author.send(content=content)


async def check_hashsums(*hashsums):
    if not hashsums:
        raise CommandFailed()

    if not all(map(lambda h: len(h) == 40 and HEXADECIMAL_REGEX.match(h), hashsums)):
        raise CommandFailed(content="SHA1 hashes are 40 hex digits long.")


async def add_content_filter(bot, guild, filters, level, hexsum, description):
    logger.info("Adding SHA1 to guild content filter '%s': %s", level.value, hexsum)

    try:
        hashsum = bytes.fromhex(hexsum)
        with bot.sql.transaction():
            if hashsum in filters[guild]:
                logger.debug("Updating existing content filter")
                bot.sql.filter.update_content_filter(guild, level, hashsum, description)
            else:
                logger.debug("Adding new content filter")
                bot.sql.filter.add_content_filter(guild, level, hashsum, description)

        filters[guild][hashsum] = (level, description)
    except Exception as error:
        logger.error("Error adding content filter", exc_info=error)
        raise CommandFailed()


async def delete_content_filter(bot, guild, filters, hexsums):
    logger.info("Removing SHA1s from guild content filter: %s", ", ".join(hexsums))

    try:
        hashsums = [bytes.fromhex(hexsum) for hexsum in hexsums]
        with bot.sql.transaction():
            for hashsum in hashsums:
                if hashsum in filters[guild]:
                    bot.sql.filter.delete_filter(guild, hashsum)
                    filters[guild].pop(hashsum, None)
                    logger.debug("Succesfully removed hashsum from filter")
                else:
                    logger.debug("Filter was not present, not deleting")
    except Exception as error:
        logger.error("Error deleting filter(s)", exc_info=error)
        raise CommandFailed()


async def show_content_filter(all_filters, message):
    if all_filters:
        contents = []
        content = StringBuilder()
        content.writeln(f"**Filtered SHA1 hashes for {message.guild.name}:**")

        # Set up filter list
        filters = {filter_type: [] for filter_type in FilterType}
        for hashsum, (filter_type, description) in all_filters.items():
            filters[filter_type].append((hashsum.hex(), description))

        # Iterate through filters
        for filter_type in FilterType:
            filter_list = filters[filter_type]
            filter_list.sort()

            content.writeln(
                f"{filter_type.emoji} {filter_type.description} hashes {filter_type.emoji}"
            )
            content.writeln("```")

            if not filter_list:
                content.writeln("(none)")
                content.writeln("```")
                continue

            for hexsum, description in filter_list:
                content.writeln(f"{hexsum} {description}")

                if len(content) > 1900:
                    content.writeln("```")
                    contents.append(str(content))
                    content.clear()
                    content.writeln("```")

            if len(content) > 4:
                content.writeln("```")
            else:
                content.clear()

        if content:
            contents.append(str(content))
    else:
        contents = (f"**No filtered SHA1 hashes for {message.guild.name}**",)

    for content in contents:
        await message.author.send(content=content)
