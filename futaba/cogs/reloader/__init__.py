#
# cogs/reloader/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Reloader


# Setup for when cog is loaded
def setup(bot):
    setup_Reloader(bot)

def setup_Reloader(bot):
    cog = Reloader(bot)
    bot.add_cog(cog)

# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_Reloader(bot)

def teardown_Reloader(bot):
    bot.remove_cog(Reloader.__name__)
