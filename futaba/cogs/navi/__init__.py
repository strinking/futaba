#
# cogs/navi/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Navi

# Setup for when cog is loaded
def setup(bot):
    setup_navi(bot)


def setup_navi(bot):
    cog = Navi(bot)
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_navi(bot)


def teardown_navi(bot):
    bot.remove_cog(Navi.__name__)
