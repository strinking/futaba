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

from futaba.cogs.abc import AbstractCog

from .simple_filter import simple_filter


class SimplewriterCog(AbstractCog):
    __slots__ = ("journal", "channel_id")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/simplewriter")
        self.channel_id = int(bot.config.optional_cogs["simplewriter"]["channel-id"])

    def setup(self):
        pass

    def cog_unload(self):
        self.bot.remove_listener(self.on_message, "on_message")
        self.bot.remove_listener(self.on_message_edit, "on_message_edit")

    async def on_message(self, message):
        await simple_filter(self, message)

    async def on_message_edit(self, before, after):
        if after:
            await simple_filter(self, after)
