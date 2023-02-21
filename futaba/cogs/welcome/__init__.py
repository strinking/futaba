#
# cogs/welcome/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .alert import Alert
from .core import Welcome
from .prune import Prune


# Setup for when cog is loaded
def setup(bot):
    setup_alert(bot)
    setup_welcome(bot)
    setup_prune(bot)


def setup_alert(bot):
    cog = Alert(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    bot.add_cog(cog)


def setup_welcome(bot):
    cog = Welcome(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_listener(cog.member_leave, "on_member_remove")
    bot.add_cog(cog)


def setup_prune(bot):
    cog = Prune(bot)
    bot.add_cog(cog)


# Remove all the cogs when cog is unloaded
def teardown(bot):
    teardown_alert(bot)
    teardown_welcome(bot)
    teardown_prune(bot)


def teardown_alert(bot):
    bot.remove_cog(Alert.__name__)


def teardown_welcome(bot):
    bot.remove_cog(Welcome.__name__)


def teardown_prune(bot):
    bot.remove_cog(Prune.__name__)
