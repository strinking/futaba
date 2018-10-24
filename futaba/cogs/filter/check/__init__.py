#
# cogs/filter/check/__init__.py
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

import discord

from futaba.enums import FilterType, LocationType, NameType
from futaba.str_builder import StringBuilder
from .common import MASK_NICK
from .file import FoundFileViolation, check_file_filter
from .name import FoundNameViolation, check_name_filter
from .text import FoundTextViolation, check_text_filter

logger = logging.getLogger(__name__)

__all__ = ["MASK_NICK", "check_message", "check_message_edit", "check_member_update"]


def filter_immune(bot, guild, member, channel=None):
    """
    Checks for certain people who are not subject to the filter's effects.
    """

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

    # Fetch most specific permissions
    if channel is None:
        perms = member.guild_permissions
    else:
        perms = channel.permissions_for(member)

    # Check admins
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


async def check_message(cog, message):
    """
    Checks the message against all applicable filters, and takes
    the appropriate action if necessary.
    """

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

    logger.debug(
        "Checking message id %d (by '%s' (%d)) for filter violations",
        message.id,
        message.author.name,
        message.author.id,
    )

    await asyncio.gather(
        check_text_filter(cog, message), check_file_filter(cog, message)
    )


async def check_message_edit(cog, before, after):
    """
    Checks the edited message against all applicable filters, and
    takes appropriate action if necessary.
    """

    logger.debug("Checking message edit")
    await check_message(cog, after)


async def check_member_join(cog, member):
    """
    Checks a new member against all text filters to ensure
    they don't have an inappropriate username or nickname.
    """

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
    """
    Checks the member update against all text filters to ensure
    they didn't change their username or nickname to something
    inappropriate.
    """

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
