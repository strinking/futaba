#
# cogs/info/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
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
    setup_Info(bot)
    setup_Alias(bot)


def setup_Info(bot):
    cog = Info(bot)
    bot.add_cog(cog)


def setup_Alias(bot):
    cog = Alias(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_Info(bot)
    teardown_Alias(bot)


def teardown_Info(bot):
    bot.remove_cog(Info.__name__)


def teardown_Alias(bot):
    bot.remove_cog(Alias.__name__)
