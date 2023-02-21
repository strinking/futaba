#
# cogs/roles/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import SelfAssignableRoles


# Setup for when cog is loaded
def setup(bot):
    setup_selfassignableroles(bot)


def setup_selfassignableroles(bot):
    cog = SelfAssignableRoles(bot)
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_selfassignableroles(bot)


def teardown_selfassignableroles(bot):
    bot.remove_cog(SelfAssignableRoles.__name__)
