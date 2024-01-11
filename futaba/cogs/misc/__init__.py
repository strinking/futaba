#
# cogs/misc/__init__.py
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

from .core import Miscellaneous
from .debug import Debugging
from .mentionable import Mentionable


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_miscellaneous(bot)
    await setup_debugging(bot)
    await setup_mentionable(bot)


async def setup_miscellaneous(bot: Bot):
    cog = Miscellaneous(bot)
    await bot.add_cog(cog)


async def setup_debugging(bot: Bot):
    cog = Debugging(bot)
    await bot.add_cog(cog)


async def setup_mentionable(bot: Bot):
    cog = Mentionable(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    bot.add_listener(cog.member_update, "on_member_update")
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_miscellaneous(bot)
    await teardown_debugging(bot)
    await teardown_mentionable(bot)


async def teardown_miscellaneous(bot: Bot):
    await bot.remove_cog(Miscellaneous.__name__)


async def teardown_debugging(bot: Bot):
    await bot.remove_cog(Debugging.__name__)


async def teardown_mentionable(bot: Bot):
    await bot.remove_cog(Mentionable.__name__)
