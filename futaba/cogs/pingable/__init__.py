#
# cogs/pingable/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Pingable


# Setup for when cog is loaded
def setup(bot):
    setup_pingable(bot)


def setup_pingable(bot):
    cog = Pingable(bot)
    bot.add_cog(cog)


def teardown(bot):
    teardown_pingable(bot)


def teardown_pingable(bot):
    bot.remove_cog(Pingable.__name__)
