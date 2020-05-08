#
# journal/impl/logging_output.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
A Listener that outputs messages to the special logger "futaba.meta.journal".
"""

import logging

from ..listener import Listener

logger = logging.getLogger("futaba.meta.journal")

__all__ = ["LoggingOutputListener"]


class LoggingOutputListener(Listener):
    async def handle(self, path, guild, content, attributes):
        """
        Logs the message to the output.
        """

        level = attributes.get("level", "info")
        assert level in ("error", "warning", "info", "debug")
        log = getattr(logger, level)

        if guild is None:
            log("[no guild] %s: %s", path, content)
        else:
            log("'%s' (%d) %s: %s", guild.name, guild.id, path, content)
