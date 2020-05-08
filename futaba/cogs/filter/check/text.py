#
# cogs/filter/check/text.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
from collections import namedtuple

import discord

from futaba.enums import FilterType, LocationType
from futaba.str_builder import StringBuilder
from futaba.utils import escape_backticks
from .common import journal_violation

logger = logging.getLogger(__name__)

__all__ = ["FoundTextViolation", "check_text_filter"]

FoundTextViolation = namedtuple(
    "FoundTextViolation",
    (
        "bot",
        "journal",
        "message",
        "content",
        "location_type",
        "filter_type",
        "filter_text",
    ),
)


async def check_text_filter(cog, message):
    # Also check embed content
    content = StringBuilder(message.content)
    for embed in message.embeds:
        embed_dict = embed.to_dict()
        content.writeln(embed_dict.get("description", ""))
        content.writeln(embed_dict.get("title", ""))

        for field in embed_dict.get("fields", []):
            content.writeln(field.get("name", ""))
            content.writeln(field.get("value", ""))

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
                        bot=cog.bot,
                        journal=cog.journal,
                        message=message,
                        content=to_check,
                        location_type=location_type,
                        filter_type=filter_type,
                        filter_text=filter_text,
                    )

    if triggered is not None:
        roles = cog.bot.sql.settings.get_special_roles(message.guild)
        await found_text_violation(triggered, roles)


async def found_text_violation(triggered, roles):
    """
    Processes a violation of the text filter. This coroutine is responsible
    for actual enforcement, based on the filter_type.
    """

    bot = triggered.bot
    journal = triggered.journal
    message = triggered.message
    content = triggered.content
    location_type = triggered.location_type
    filter_type = triggered.filter_type
    filter_text = triggered.filter_text

    logger.info(
        "Punishing %s filter violation (%r, level %s) by '%s' (%d)",
        location_type.value,
        filter_text,
        filter_type.value,
        message.author.name,
        message.author.id,
    )

    severity = filter_type.level

    # Escape content for display
    escaped_filter_text = escape_backticks(filter_text)
    escaped_content = escape_backticks(content)

    if len(escaped_content) > 1800:
        escaped_content = escaped_content[:1800] + " ... (message too long)"

    async def message_violator():
        logger.debug("Sending message to user who violated the filter")
        response = StringBuilder(
            f"The message you posted in {message.channel.mention} violates a {location_type.value} "
            f"{filter_type.value} filter disallowing `{escaped_filter_text}`."
        )

        if severity >= FilterType.JAIL.level:
            if roles.jail is not None:
                response.writeln(
                    "This offense is serious enough to warrant immediate revocation of posting privileges.\n"
                    f"As such, you have been assigned the `{roles.jail.name}` role, until a moderator clears you."
                )

        await message.author.send(content=str(response))
        response.clear()

        if message.content != content:
            embed_caveat = "(including text from all embeds attached to your message)"
        else:
            embed_caveat = ""

        embed = discord.Embed(description=content)
        embed.timestamp = discord.utils.snowflake_time(message.id)
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.avatar_url
        )
        to_send = f"The content of the deleted message {embed_caveat} is:"
        await message.author.send(content=to_send, embed=embed)

        response.writeln("or, quoted:")
        response.writeln("```")
        response.writeln(escaped_content)
        response.writeln("```")
        response.writeln("Contact a moderator if you have questions.")
        await message.author.send(content=str(response))

    if severity >= FilterType.FLAG.level:
        logger.info("Notifying staff of filter violation")
        journal_violation(
            journal, "text", message, filter_type, escaped_filter_text, escaped_content
        )

    if severity >= FilterType.BLOCK.level:
        logger.info(
            "Deleting inappropriate message id %d and notifying user", message.id
        )
        await asyncio.gather(message.delete(), message_violator())

    if severity >= FilterType.JAIL.level:
        if roles.jail is None:
            logger.info(
                "Jailing user for inappropriate message, except there is no jail role configured!"
            )
            content = f"Cannot jail {message.author.mention} for filter violation because no jail role is set!"
            journal.send("text/jail", message.guild, content, icon="warning")
        else:
            logger.info("Jailing user for inappropriate message")
            await bot.punish.jail(
                message.guild, message.author, "Jailed for violating file filter"
            )
