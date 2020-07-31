#
# cogs/optional/simplewriter/simple_filter.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Filters messages through the allowed wordlist, deleting unallowed words.
"""

import logging
import re
from datetime import datetime

import discord
from discord import MessageType

from futaba.utils import plural

from .words import core_words_list

logger = logging.getLogger(__name__)

__all__ = ["simple_filter"]


async def simple_filter(cog, message):
    """
    Filter Discord messages for the simplewriter channel
    """

    # Not DMs
    if message.guild is None:
        return

    # Not a special message type
    if message.type != MessageType.default:
        return

    # Make sure we actually can remove this message
    if not message.channel.permissions_for(message.guild.me).manage_messages:
        return

    # Don't filter bot messages
    if message.author.id == cog.bot.user.id:
        return

    if message.channel.id != int(
        cog.bot.config.optional_cogs["simplewriter"]["channel-id"]
    ):
        return

    logger.debug(
        "Message in simplewriter channel. Checking message id %d (by '%s' (%d)) against simplewriter core words list",
        message.id,
        message.author.name,
        message.author.id,
    )

    split = re.split(r"\W+", message.content)
    bad_words = []
    for word in split:
        cleaned = word.strip()
        if not cleaned: continue
        if not cleaned.lower() in core_words_list:
            if not cleaned in bad_words:
                try:  # test to see if input is a number
                    int(cleaned)
                except ValueError:
                    bad_words.append(cleaned)

    if len(bad_words) > 0:
        await message.delete()

        content = (
            f"Message id {message.id} (by '{message.author.name}' ({message.author.id})) filtered from "
            "simplewriter channel"
        )
        cog.journal.send("message/delete", message.guild, content)

        bad_words_plural = plural(len(bad_words))
        article = "some" if len(bad_words) > 1 else "a"

        help_embed = discord.Embed()
        help_embed.color = discord.Color.red()
        help_embed.title = f"You used {article} less simple word{bad_words_plural}."
        help_embed.description = (
            f"Your message in {message.channel.mention} has been removed.\n"
            "You can use [xkcd's simplewriter](https://xkcd.com/simplewriter) "
            "to see what words are valid in this channel."
        )
        help_embed.timestamp = datetime.now()
        help_embed.add_field(name="Full message", value=message.content)
        help_embed.add_field(
            name=f"Bad word{bad_words_plural}", value=", ".join(bad_words)
        )
        help_embed.set_footer(text=message.id)

        dm_channel = message.author.dm_channel or await message.author.create_dm()
        await dm_channel.send(embed=help_embed)
