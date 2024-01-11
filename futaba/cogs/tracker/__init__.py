#
# cogs/tracking/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Emmie Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from discord.ext.commands.bot import Bot

from .core import Tracker, LISTENERS


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_tracker(bot)


async def setup_tracker(bot: Bot):
    cog = Tracker(bot)
    for listener in LISTENERS:
        bot.add_listener(getattr(cog, listener), listener)
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_tracker(bot)


async def teardown_tracker(bot: Bot):
    await bot.remove_cog(Tracker.__name__)
