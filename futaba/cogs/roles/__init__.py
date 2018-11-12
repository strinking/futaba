#
# cogs/roles/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import SelfAssignableRoles
from .reapplication import RoleReapplication


def setup(bot):
    cog = RoleReapplication(bot)
    bot.add_listener(cog.member_join, "on_member_join")
    bot.add_listener(cog.member_update, "on_member_update")
    bot.add_cog(cog)

    cog = SelfAssignableRoles(bot)
    bot.add_cog(cog)
