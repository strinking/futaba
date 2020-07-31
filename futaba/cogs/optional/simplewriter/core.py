#
# cogs/optional/simplewriter/core.py
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
A thing that lets you write stuff in one word box, but only if it's made up of
the first ten hundred most used words of the language.

(https://xkcd.com/simplewriter)
"""

from futaba.utils import async_partial
from futaba.cogs.abc import AbstractCog

from .listeners import on_message, on_message_edit


class SimplewriterCog(AbstractCog):
    __slots__ = ("journal", "on_message", "on_message_edit", "channel_id")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/simplewriter")
        self.on_message = async_partial(on_message, self)
        self.on_message_edit = async_partial(on_message_edit, self)
        self.channel_id = int(bot.config.optional_cogs["simplewriter"]["channel-id"])

    def setup(self):
        pass

    def cog_unload(self):
        self.bot.remove_listener(self.on_message, "on_message")
        self.bot.remove_listener(self.on_message_edit, "on_message_edit")
