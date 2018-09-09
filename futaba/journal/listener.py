#
# journal/listener.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging

logger = logging.getLogger(__name__)

__all__ = [
    'Listener',
]

class Listener:
    __slots__ = (
        'router',
        'path',
        'handler',
        'recursive',
        'filter',
    )

    def __init__(self, router, path, handler, recursive=True, filter=None):
        self.router = router
        self.path = path
        self.handler = handler
        self.recursive = recursive
        self.filter = filter

    def check(self, path, content, attributes):
        if self.filter is not None:
            if not self.filter(path, content, attributes):
                logger.debug("Filter rejected journal entry")
                return False

        if not self.recursive:
            if self.path != path:
                logger.debug("Ignoring non-recursive listener")
                return False

        return True
