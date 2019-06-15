#
# cogs/optional/statbot/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Statbot
from .citizen import Citizen
from .sql import StatbotSqlHandler

def setup(bot):
    sql = StatbotSqlHandler(bot.config.optional_cogs["statbot"]["url"])

    cog = Statbot(bot, sql)
    bot.add_cog(cog)

    cog = Citizen(bot, sql)
    bot.add_cog(cog)
