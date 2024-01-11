#
# cogs/moderation/__init__.py
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

from .cleanup import Cleanup
from .core import Moderation
from .manual_mod_action_warn import ManualModActionWarn


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_cleanup(bot)
    await setup_moderation(bot)
    await setup_manualmodactionwarn(bot)


async def setup_cleanup(bot: Bot):
    cog = Cleanup(bot)
    await bot.add_cog(cog)


async def setup_moderation(bot: Bot):
    cog = Moderation(bot)
    await bot.add_cog(cog)


async def setup_manualmodactionwarn(bot: Bot):
    cog = ManualModActionWarn(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_listener(cog.member_remove, "on_member_remove")
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_cleanup(bot)
    await teardown_moderation(bot)
    await teardown_manualmodactionwarn(bot)


async def teardown_cleanup(bot: Bot):
    await bot.remove_cog(Cleanup.__name__)


async def teardown_moderation(bot: Bot):
    await bot.remove_cog(Moderation.__name__)


async def teardown_manualmodactionwarn(bot: Bot):
    await bot.remove_cog(ManualModActionWarn.__name__)
