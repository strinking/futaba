#
# cogs/tracking/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Tracker, LISTENERS, get_removal_cause

# Setup for when cog is loaded
def setup(bot):
    setup_Tracker(bot)


def setup_Tracker(bot):
    cog = Tracker(bot)
    for listener in LISTENERS:
        bot.add_listener(getattr(cog, listener), listener)
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_Tracker(bot)


def teardown_Tracker(bot):
    bot.remove_cog(Tracker.__name__)
