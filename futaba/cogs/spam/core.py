"""
Cog for handling cross-channel spam.
"""

import logging
from datetime import datetime

import discord
from discord import guild
from discord import channel
from discord.ext import commands
from futaba.cogs.filter.check import check_message

from futaba.exceptions import CommandFailed
from futaba.str_builder import StringBuilder
from ..abc import AbstractCog
from collections import deque, OrderedDict
from discord import MessageType
from hashlib import sha1

logger = logging.getLogger(__name__)

__all__ = ["Spam"]


class Spam(AbstractCog):
    __slots__ = ()

    def __init__(self, bot):
        super().__init__(bot)
        self.history = dict()
        bot.add_listener(self.check_message, "on_message")
        bot.add_listener(self.check_message_edit, "on_message_edit")
        self.journal = bot.get_broadcaster("/cross-post")

    def setup(self):
        pass

    async def check_message(self, message):
        # Don't filter PMs
        if message.guild is None:
            return

        # Don't check special messages
        if message.type != MessageType.default:
            return

        # Check that we actually have permissions to delete
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        # TODO: rest of checks are in filter/check/init, kinda weird that theres no generic
        # method to check if rules apply to user X

        guild_history = self.history.get(message.guild.id)
        if guild_history is None:
            guild_history = LRUDict(maxlen=126)
            self.history[message.guild.id] = guild_history

        message_history = guild_history.get(message.author.id)
        if message_history is None:
            message_history = LRUDict(maxlen=8)
            guild_history[message.author.id] = message_history

        logger.info(message_history)

        message_hash = sha1(message.content.encode("utf-8")).hexdigest()
        message_posts = message_history.get(message_hash)
        if message_posts is None:
            message_posts = { 'messages': [], 'channels': set() }
            message_history[message_hash] = message_posts

        message_posts['channels'].add(message.channel.id)
        message_posts['messages'].append(message)

        if len(message_posts['channels']) >= 5:
            await self.punish(message, message_posts)

    async def check_message_edit(self, before, after):
        await self.check_message(after)

    async def punish(self, message, message_posts):
        roles = self.bot.sql.settings.get_special_roles(message.guild)


        if roles.jail_role is None:
            logger.info(
                "Jailing user for cross-post, except there is no jail role configured!"
            )
            content = f"Cannot jail {message.author.mention} for cross-post violation because no jail role is set!"
            self.journal.send("cross-post/jail", message.guild, content, icon="warning")
        else:
            if not roles.jail_role in message.author.roles:
                response = StringBuilder()
                response.writeln(
                    f"The message you posted in {message.channel.mention} has been reposted in multiple channels by you."
                )
                response.writeln(
                    f"As such, you have been asssigned the `{roles.jail_role.name}` role, until a moderator clears you."
                )

                kwargs = { "content": str(response) }
                await message.author.send(**kwargs)
                await self.bot.punish.jail(message.guild, message.author, "Jailed for cross-posting")

            await self.delete_messages(message_posts)

    async def delete_messages(self, message_posts):
        messages = message_posts['messages']
        for message in messages:
            await message.delete()


class LRUDict(OrderedDict):
    'Limit size, evicting the least recently looked-up key when full'

    def __init__(self, maxlen=128, *args, **kwds):
        self.maxlen = maxlen
        super().__init__(*args, **kwds)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxlen:
            oldest = next(iter(self))
            del self[oldest]
