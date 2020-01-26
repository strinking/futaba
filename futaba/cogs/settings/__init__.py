#
# cogs/settings/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Settings

# Setup for when cog is loaded
def setup(bot):
    setup_Settings(bot)


def setup_Settings(bot):
    cog = Settings(bot)
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_Settings(bot)


def teardown_Settings(bot):
    bot.remove_cog(Settings.__name__)
