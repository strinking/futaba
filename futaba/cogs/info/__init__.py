#
# cogs/info/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .alias import Alias
from .core import Info


# Setup for when cog is loaded
def setup(bot):
    setup_info(bot)
    setup_alias(bot)


def setup_info(bot):
    cog = Info(bot)
    bot.add_cog(cog)


def setup_alias(bot):
    cog = Alias(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_info(bot)
    teardown_alias(bot)


def teardown_info(bot):
    bot.remove_cog(Info.__name__)


def teardown_alias(bot):
    bot.remove_cog(Alias.__name__)
