#
# journal/listener.py
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
from abc import abstractmethod
from pathlib import PurePath

logger = logging.getLogger(__name__)

__all__ = ["Listener"]


class Listener:
    def __init__(self, router, path, recursive=True):
        self.router = router
        self.path = PurePath(path)
        self.recursive = recursive

    def check(self, path, guild, content, attributes):
        if not self.filter(path, guild, content, attributes):
            logger.debug("Filter rejected journal entry")
            return False

        if not self.recursive:
            if self.path != path:
                logger.debug("Ignoring non-recursive listener")
                return False

        return True

    # This method is meant to provide a default implementation that can be overriden.
    # pylint: disable=no-self-use
    def filter(self, path, guild, content, attributes):
        """
        Overridable method for further filtering listener events that are passed through.
        """

        return True

    @abstractmethod
    async def handle(self, path, guild, content, attributes):
        """
        Abstract method for handling the event, in whatever way
        the implementation decides.
        """

        # - pass -
