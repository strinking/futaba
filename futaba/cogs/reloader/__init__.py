#
# cogs/reloader/__init__.py
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

from .core import Reloader


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_reloader(bot)


async def setup_reloader(bot: Bot):
    cog = Reloader(bot)
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_reloader(bot)


async def teardown_reloader(bot: Bot):
    await bot.remove_cog(Reloader.__name__)
