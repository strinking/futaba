#
# cogs/info/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .alias import Alias
from .core import Info


def setup(bot):
    cog = Info(bot)
    bot.add_cog(cog)

    cog = Alias(bot)
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_cog(cog)
