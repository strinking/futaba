#
# cogs/misc/core.py
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
Cog for miscellaneous commands that don't really belong anywhere else.
"""

import logging
import random
from datetime import datetime
from hashlib import sha1

import discord
from discord.ext import commands

from futaba.download import download_links
from futaba.exceptions import CommandFailed
from futaba.str_builder import StringBuilder
from futaba.unicode import unicode_repr
from futaba.utils import URL_REGEX
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Miscellaneous"]

SHA1_ERROR_MESSAGE = "Error downloading file".ljust(40)


class Miscellaneous(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/misc")

    def setup(self):
        pass

    @commands.command(name="ping")
    async def ping(self, ctx):
        """Determines the bot's current latency."""

        duration = datetime.now() - discord.utils.snowflake_time(ctx.message.id)
        ms = duration.microseconds / 1000
        content = f"Pong! `{ms} ms`"

        await ctx.send(content=content)
        self.journal.send("ping", ctx.guild, content, icon="ok")

    @commands.command(name="randomemoji", aliases=["randemoji", "remoji"])
    async def random_emoji(self, ctx):
        """
        Sends a random emoji from any the servers the bot is connected to.
        """

        if not self.bot.emojis:
            raise CommandFailed()

        emoji = random.choice(self.bot.emojis)
        await ctx.send(content=str(emoji))
        if isinstance(ctx.channel, discord.DMChannel):
            chan_name = ctx.channel.recipient.name
        else:
            chan_name = ctx.channel.mention

        content = f"Sent random emoji {emoji} to {chan_name}."
        self.journal.send(
            "emoji/random",
            ctx.guild,
            content,
            icon="fun",
            channel=ctx.channel,
            emoji=emoji,
        )

    @commands.command(name="unicoderepr", aliases=["unicrepr", "urepr"])
    async def unicode_repr(self, ctx, *, text: str):
        """Outputs the Python representation of the given unicode string."""

        text_repr = unicode_repr(text)
        await ctx.send(content=f"`{text_repr}`")

    @commands.command(name="sha1sum", aliases=["sha1", "sha", "hashsum", "hash"])
    async def sha1sum(self, ctx, *urls: str):
        """Gives the SHA1 hashes of any files attached to the message."""

        # Check all URLs
        links = []
        for url in urls:
            match = URL_REGEX.match(url)
            if match is None:
                raise CommandFailed(content=f"Not a valid url: {url}")
            links.append(match[1])
        links.extend(attach.url for attach in ctx.message.attachments)

        # Get list of "names"
        names = list(urls)
        names.extend(attach.filename for attach in ctx.message.attachments)

        # Send error if no URLS
        if not links:
            raise CommandFailed(content="No URLs listed or files attached.")

        # Download and check files
        contents = []
        content = StringBuilder("Hashes:\n```")
        buffers = await download_links(links)
        for i, binio in enumerate(buffers):
            if binio is None:
                hashsum = SHA1_ERROR_MESSAGE
            else:
                hashsum = sha1(binio.getbuffer()).hexdigest()

            content.writeln(f"{hashsum} {names[i]}")
            if len(content) > 1920:
                contents.append(content)
                if i < len(buffers) - 1:
                    content.clear()
                    content.writeln("```")

        if len(content) > 4:
            content.writeln("```")
            contents.append(content)

        for content in contents:
            await ctx.send(content=str(content))
