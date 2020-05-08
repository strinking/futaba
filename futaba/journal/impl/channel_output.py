#
# journal/impl/channel_output.py
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
A Listener that outputs messages to the configured Discord channel.
"""

import logging

from futaba.utils import copy_discord_file
from ..listener import Listener

logger = logging.getLogger(__name__)

__all__ = ["ChannelOutputListener"]


class ChannelOutputListener(Listener):
    def __init__(self, router, path, channel, recursive=True):
        super().__init__(router, path, recursive)
        self.channel = channel

    def filter(self, path, guild, content, attributes):
        """
        Ensures that this event is actually meant for this channel output logger.
        """

        # No guild
        if guild is None:
            return False

        # Wrong guild
        if self.channel not in guild.channels:
            return False

        return True

    async def handle(self, path, guild, content, attributes):
        """
        Send the message to the given channel, applying the icon if applicable.
        """

        kwargs = {"content": content}

        if "embed" in attributes:
            kwargs["embed"] = attributes["embed"]
        if "file" in attributes:
            kwargs["file"] = copy_discord_file(attributes["file"])
        if "files" in attributes:
            kwargs["files"] = list(map(copy_discord_file, attributes["files"]))

        coro = self.channel.send(**kwargs)
        self.router.bot.queue.push(coro)
