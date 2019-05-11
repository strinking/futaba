#
# cogs/filter/check/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
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
from discord import MessageType

from futaba.enums import FilterType, LocationType, NameType
from futaba.permissions import is_admin_perm
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
    if member.id == bot.id:
        logger.debug("Filter check: ignoring self")
        return True

    # Check if bots have filter immunity
    filter_settings = bot.sql.filter.get_settings(guild)
    if filter_settings.bot_immune:
        if member.bot:
            logger.debug("Filter check: this server ignores all bots")
            return True

    # Ignore owners
    if member.id in bot.config.owner_ids:
        logger.debug("Filter check: is an owner")
        return True

    # Check manually-added users
    if bot.sql.filter.user_is_filter_immune(guild, member):
        logger.debug("Filter check: added to filter immunity list")
        return True

    # In the case where the author isn't a Member yet
    if not isinstance(member, discord.Member):
        id = member.id
        member = guild.get_member(id)
        if member is None:
            logger.warning("Cannot find member for user ID %d", id)
            logger.debug("Filter check: isn't a member yet")
            return False

    # Fetch most specific permissions
    if channel is None:
        perms = member.guild_permissions
    else:
        perms = channel.permissions_for(member)

    # Check admins
    if is_admin_perm(perms):
        logger.debug("Filter check: is an admin")
        return True

    # Check channel moderators (if enabled)
    if filter_settings.manage_messages_immune:
        if perms.manage_messages:
            logger.debug("Filter check: has manage messages")
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

    # Don't check special messages
    if message.type != MessageType.default:
        logger.debug("Ignoring non-default message")
        return

    # Check that we actually have permissions to delete
    if not message.channel.permissions_for(message.guild.me).manage_messages:
        logger.debug(
            "Lacks permissions to delete messages in guild '%s' (%d)",
            message.guild.name,
            message.guild.id,
        )
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
        logger.debug(
            "Lacks permissions to manage roles in guild '%s' (%d)",
            member.guild.name,
            member.guild.id,
        )
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

    # Check that we actually have permissions to manage roles
    guild = before.guild
    if not guild.me.guild_permissions.manage_roles:
        logger.debug(
            "Lacks permissions to manage roles in guild '%s' (%d)",
            after.guild.name,
            after.guild.id,
        )
        return

    # Cannot be parallelized because we can only renick if the username is ok
    if before.name != after.name:
        await check_name_filter(cog, after.name, NameType.USER, after)

    if before.nick != after.nick and after.nick is not None:
        if after.nick == MASK_NICK:
            logger.debug("User has masked nickname, ignoring")
            return

        await check_name_filter(cog, after.nick, NameType.NICK, after)
