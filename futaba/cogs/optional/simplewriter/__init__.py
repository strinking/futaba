#
# cogs/optional/simplewriter/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from .core import SimplewriterCog


def setup(bot):
    setup_simplewriter(bot)


def setup_simplewriter(bot):
    cog = SimplewriterCog(bot)
    bot.add_listener(cog.on_message, "on_message")
    bot.add_listener(cog.on_message_edit, "on_message_edit")
    bot.add_cog(cog)


def teardown(bot):
    teardown_simplewriter(bot)


def teardown_simplewriter(bot):
    bot.remove_cog(SimplewriterCog.__name__)
