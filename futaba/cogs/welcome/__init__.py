#
# cogs/welcome/__init__.py
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

from .alert import Alert
from .core import Welcome
from .prune import Prune


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_alert(bot)
    await setup_welcome(bot)
    await setup_prune(bot)


async def setup_alert(bot: Bot):
    cog = Alert(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    await bot.add_cog(cog)


async def setup_welcome(bot: Bot):
    cog = Welcome(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_listener(cog.member_leave, "on_member_remove")
    await bot.add_cog(cog)


async def setup_prune(bot: Bot):
    cog = Prune(bot)
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_alert(bot)
    await teardown_welcome(bot)
    await teardown_prune(bot)


async def teardown_alert(bot: Bot):
    await bot.remove_cog(Alert.__name__)


async def teardown_welcome(bot: Bot):
    await bot.remove_cog(Welcome.__name__)


async def teardown_prune(bot: Bot):
    await bot.remove_cog(Prune.__name__)
