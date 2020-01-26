#
# cogs/misc/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Miscellaneous
from .debug import Debugging
from .mentionable import Mentionable

# Setup for when cog is loaded
def setup(bot):
    setup_Miscellaneous(bot)
    setup_Debugging(bot)
    setup_Mentionable(bot)


def setup_Miscellaneous(bot):
    cog = Miscellaneous(bot)
    bot.add_cog(cog)


def setup_Debugging(bot):
    cog = Debugging(bot)
    bot.add_cog(cog)


def setup_Mentionable(bot):
    cog = Mentionable(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_Miscellaneous(bot)
    teardown_Debugging(bot)
    teardown_Mentionable(bot)


def teardown_Miscellaneous(bot):
    bot.remove_cog(Miscellaneous.__name__)


def teardown_Debugging(bot):
    bot.remove_cog(Debugging.__name__)


def teardown_Mentionable(bot):
    bot.remove_cog(Mentionable.__name__)
