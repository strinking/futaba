#
# cogs/journal/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import Journal


def setup(bot):
    setup_Journal(bot)

def setup_Journal(bot):
    cog = Journal(bot)
    bot.add_cog(cog)

def teardown(bot):
    teardown_Journal(bot)

def teardown_Journal(bot):
    bot.remove_cog(Journal.__name__)