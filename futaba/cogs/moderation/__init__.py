#
# cogs/moderation/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .cleanup import Cleanup
from .core import Moderation
from .manual_mod_action_warn import ManualModActionWarn


# Setup for when cog is loaded
def setup(bot):
    setup_cleanup(bot)
    setup_moderation(bot)
    setup_manualmodactionwarn(bot)


def setup_cleanup(bot):
    cog = Cleanup(bot)
    bot.add_cog(cog)


def setup_moderation(bot):
    cog = Moderation(bot)
    bot.add_cog(cog)


def setup_manualmodactionwarn(bot):
    cog = ManualModActionWarn(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_listener(cog.member_remove, "on_member_remove")
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_cleanup(bot)
    teardown_moderation(bot)
    teardown_manualmodactionwarn(bot)


def teardown_cleanup(bot):
    bot.remove_cog(Cleanup.__name__)


def teardown_moderation(bot):
    bot.remove_cog(Moderation.__name__)


def teardown_manualmodactionwarn(bot):
    bot.remove_cog(ManualModActionWarn.__name__)
