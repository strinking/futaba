#
# cogs/info/__init__.py
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

from .alias import Alias
from .core import Info


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_info(bot)
    await setup_alias(bot)


async def setup_info(bot: Bot):
    cog = Info(bot)
    await bot.add_cog(cog)


async def setup_alias(bot: Bot):
    cog = Alias(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_info(bot)
    await teardown_alias(bot)


async def teardown_info(bot: Bot):
    await bot.remove_cog(Info.__name__)


async def teardown_alias(bot: Bot):
    await bot.remove_cog(Alias.__name__)
