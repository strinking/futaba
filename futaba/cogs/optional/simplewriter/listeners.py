#
# cogs/optional/simplewriter/listeners.py
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
discord.py listeners for simplewriter
"""

from .simple_filter import simple_filter

__all__ = ["on_message", "on_message_edit"]


async def on_message(cog, message):
    await simple_filter(cog, message)


async def on_message_edit(cog, before, after):
    if after:
        await simple_filter(cog, after)
