#
# cogs/moderation/cleanup.py
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
Commands related to cleaning up messages in bulk.
"""

import json
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.dict_convert import message_dict
from futaba.exceptions import CommandFailed
from futaba.str_builder import StringBuilder
from futaba.unicode import normalize_caseless
from futaba.utils import escape_backticks, user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Cleanup"]


def is_discord_id(number):
    return 10 ** 15 <= number < 10 ** 21


class _Counter:
    """ Counter that escapes issues with local scoping by being modifiable in-place. """

    __slots__ = ("value",)

    def __init__(self, value=0):
        self.value = value

    def __lt__(self, other):
        return self.value < other

    def incr(self):
        self.value += 1


class Cleanup(AbstractCog):
    __slots__ = ("journal", "dump")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/moderation/cleanup")
        self.dump = bot.get_broadcaster("/dump/moderation/cleanup")

    def setup(self):
        pass

    async def check_count(self, ctx, count):
        embed = discord.Embed(colour=discord.Colour.red())
        max_count = self.bot.sql.settings.get_max_delete_messages(ctx.guild)
        if count < 1:
            embed.description = f"Invalid message count: {count}"
            raise CommandFailed(embed=embed)

        if is_discord_id(count):
            prefix = self.bot.prefix(ctx.guild)
            embed.description = (
                "This looks like a Discord ID. If you want to delete all "
                f"messages up to a message ID, use `{prefix}cleanupid`."
            )
            raise CommandFailed(embed=embed)

        if count > max_count:
            embed.description = (
                "Count too high. Maximum configured for this guild is "
                f"`{max_count}`."
            )
            raise CommandFailed(embed=embed)

    @staticmethod
    def dump_messages(messages):
        buffer = StringBuilder()
        obj = list(map(message_dict, reversed(messages)))
        json.dump(obj, buffer, ensure_ascii=True, indent=4)
        return obj, discord.File(buffer.bytes_io(), filename="deleted-messages.json")

    @commands.command(name="cleanup", aliases=["clean"])
    @commands.guild_only()
    @permissions.check_perm("manage_messages")
    async def cleanup(self, ctx, count: int, channel: discord.TextChannel = None):
        """ Deletes the last <count> messages, not including this command. """

        await self.check_count(ctx, count)

        if channel is None:
            channel = ctx.channel

        # Delete the messages
        messages = await channel.purge(limit=count, before=ctx.message, bulk=True)

        # Send journal events
        causer = user_discrim(ctx.author)
        content = f"{causer} deleted {len(messages)} messages in {channel.mention}"
        self.journal.send(
            "count",
            ctx.guild,
            content,
            icon="delete",
            count=count,
            channel=channel,
            messages=messages,
            cause=ctx.author,
        )

        obj, file = self.dump_messages(messages)
        content = f"Cleanup by {causer} in {channel.mention} deleted these messages:"
        self.dump.send(
            "count", ctx.guild, content, icon="delete", messages=obj, file=file
        )

    @commands.command(name="cleanupid", aliases=["cleanid"])
    @commands.guild_only()
    @permissions.check_perm("manage_messages")
    async def cleanup_id(
        self, ctx, message_id: int, channel: discord.TextChannel = None
    ):
        """ Deletes all messages from the passed message ID to the present. """

        if channel is None:
            channel = ctx.channel

        # Make sure it's an ID
        if not is_discord_id(message_id):
            embed = discord.Embed(colour=discord.Colour.red())
            embed.set_author(name="Won't delete to message ID")
            embed.description = (
                f"The given number `{message_id}` doesn't look like a Discord ID."
            )
            raise CommandFailed(embed=embed)

        # Make sure it's not actually a user ID
        try:
            user = await self.bot.fetch_user(message_id)
        except discord.NotFound:
            pass
        else:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                f"The passed ID is for user {user.mention}. Did you copy the message ID or the user ID?\n\n"
                f"Not deleting. If you'd like to delete this far, specify the message count directly instead."
            )
            raise CommandFailed(embed=embed)

        # Delete the messages before the message ID
        max_count = self.bot.sql.settings.get_max_delete_messages(ctx.guild)
        messages = await channel.purge(
            limit=max_count,
            check=lambda message: message.id >= message_id,
            before=ctx.message,
            bulk=True,
        )

        if len(messages) == max_count and messages[0].id != message_id:
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = (
                f"This guild only allows `{max_count}` messages to be deleted at a time. "
                f"Because of this limitation, message ID `{message_id}` was not actually deleted."
            )
            await ctx.send(embed=embed)

        # Send journal events
        causer = user_discrim(ctx.author)
        content = (
            f"{causer} deleted {len(messages)} messages in "
            f"{channel.mention} until message ID {message_id}"
        )
        self.journal.send(
            "id",
            ctx.guild,
            content,
            icon="delete",
            message_id=message_id,
            messages=messages,
            cause=ctx.author,
        )

        obj, file = self.dump_messages(messages)
        content = (
            f"Cleanup by {causer} until message ID {message_id} in "
            f"{channel.mention} deleted these messages"
        )
        self.dump.send("id", ctx.guild, content, icon="delete", messages=obj, file=file)

    @commands.command(name="cleanupuser", aliases=["cleanuser"])
    @commands.guild_only()
    @permissions.check_perm("manage_messages")
    async def cleanup_user(
        self, ctx, user: discord.User, count: int, channel: discord.TextChannel = None
    ):
        """ Deletes the last <count> messages created by the given user. """

        await self.check_count(ctx, count)

        if channel is None:
            channel = ctx.channel

        # Deletes the messages by the user
        deleted = _Counter()

        def check(message):
            if deleted < count:
                if user == message.author:
                    deleted.incr()
                    return True
            return False

        messages = await channel.purge(
            limit=count * 2, check=check, before=ctx.message, bulk=True
        )

        # Send journal events
        causer = user_discrim(ctx.author)
        content = f"{causer} deleted {len(messages)} messages in {channel.mention} by {user.mention}"
        self.journal.send(
            "user",
            ctx.guild,
            content,
            icon="delete",
            count=count,
            channel=channel,
            messages=messages,
            user=user,
            cause=ctx.author,
        )

        obj, file = self.dump_messages(messages)
        content = f"Cleanup by {causer} of {user.mention} in {channel.mention} deleted these messages:"
        self.dump.send(
            "user", ctx.guild, content, icon="delete", messages=obj, file=file
        )

    @commands.command(name="purgeuser")
    @commands.guild_only()
    @permissions.check_admin()
    async def cleanup_purge(self, ctx, user: discord.User):
        """ Deletes full Discord message history of <user> from every channel in guild. """

        # Deletes the messages by the user
        def check(message):
            if user == message.author:
                return True
            return False

        channels = []
        messages = []

        for channel in ctx.guild.text_channels:
            this_channel = await channel.purge(
                limit=None, check=check, before=ctx.message, bulk=True
            )
            if len(this_channel) > 0:
                channels.append(channel)
                messages += this_channel

        # Send journal events
        causer = user_discrim(ctx.author)
        content = f"{causer} deleted {len(messages)} messages by {user.mention} from {len(channels)} channels"
        self.journal.send(
            "user",
            ctx.guild,
            content,
            icon="delete",
            channels=channels,
            messages=messages,
            user=user,
            cause=ctx.author,
        )

        obj, file = self.dump_messages(messages)
        content = f"Purge by {causer} of {user.mention} from {len(channels)} channels deleted these messages:"
        self.dump.send(
            "user", ctx.guild, content, icon="delete", messages=obj, file=file
        )

    @commands.command(name="cleanuptext", aliases=["cleantext"])
    @commands.guild_only()
    @permissions.check_perm("manage_messages")
    async def cleanup_text(
        self, ctx, text: str, count: int, channel: discord.TextChannel = None
    ):
        """ Deletes the last <count> messages with the given text. """

        await self.check_count(ctx, count)

        if channel is None:
            channel = ctx.channel

        # Deletes the messages with the text
        text = normalize_caseless(text)
        deleted = _Counter()

        def check(message):
            if deleted < count:
                if text in normalize_caseless(message.content):
                    deleted.incr()
                    return True
            return False

        messages = await channel.purge(
            limit=count * 2, check=check, before=ctx.message, bulk=True
        )

        # Send journal events
        text = escape_backticks(text)
        causer = user_discrim(ctx.author)
        content = f"{causer} deleted {len(messages)} messages in {channel.mention} matching `{text}`"
        self.journal.send(
            "text",
            ctx.guild,
            content,
            icon="delete",
            count=count,
            channel=channel,
            messags=messages,
            text=text,
            cause=ctx.author,
        )

        obj, file = self.dump_messages(messages)
        content = f"Cleanup by {causer} in {channel.mention} of `{text}` deleted these messages:"
        self.dump.send(
            "text", ctx.guild, content, icon="delete", messages=obj, file=file
        )
