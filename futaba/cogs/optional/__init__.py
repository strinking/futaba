#
# cogs/optional/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging

logger = logging.getLogger(__name__)


def setup(bot):
    for cog_name, options in bot.config.optional_cogs.items():
        enabled = options["enabled"]
        logger.info(
            "Optional cog: %s %s", " [ENABLED]" if enabled else "[DISABLED]", cog_name
        )

        if enabled:
            bot.reloader_cog.load_cog(f"optional.{cog_name}")
