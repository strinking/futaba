#
# cogs/optional/statbot/__init__.py
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

from .core import Statbot


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_statbot(bot)


async def setup_statbot(bot: Bot):
    cog = Statbot(bot)
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_statbot(bot)


async def teardown_statbot(bot: Bot):
    await bot.remove_cog(Statbot.__name__)
