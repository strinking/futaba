#
# cogs/moderation/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .cleanup import Cleanup
from .core import Moderation
from .manual_mod_action_warn import ManualModActionWarn


def setup(bot):
    cog = Cleanup(bot)
    bot.add_cog(cog)

    cog = Moderation(bot)
    bot.add_cog(cog)

    cog = ManualModActionWarn(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_listener(cog.member_remove, "on_member_remove")
    bot.add_cog(cog)
