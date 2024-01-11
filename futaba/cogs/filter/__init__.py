#
# cogs/filter/__init__.py
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

from futaba.utils import async_partial
from .check import check_message, check_message_edit
from .manage import add_filter, delete_filter, show_filter
from .core import Filtering


# Setup for when cog is loaded
async def setup(bot: Bot):
    await setup_filtering(bot)


async def setup_filtering(bot: Bot):
    cog = Filtering(bot)
    bot.add_listener(cog.check_message, "on_message")
    bot.add_listener(cog.check_message_edit, "on_message_edit")
    bot.add_listener(cog.check_member_join, "on_member_join")
    bot.add_listener(cog.check_member_update, "on_member_update")
    await bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
async def teardown(bot: Bot):
    await teardown_filtering(bot)


async def teardown_filtering(bot: Bot):
    await bot.remove_cog(Filtering.__name__)
