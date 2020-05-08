#
# journal/broadcaster.py
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
from pathlib import PurePath

from .event import JournalEvent

logger = logging.getLogger(__name__)

__all__ = ["Broadcaster"]


class Broadcaster:
    __slots__ = ("router", "path")

    def __init__(self, router, path):
        self.router = router
        self.path = PurePath(path)
        assert len(self.path.parts) > 1, "Cannot broadcast on the root"

    def send(self, subpath, guild, content, **attributes):
        # Get full path
        subpath = PurePath(subpath)
        assert not subpath.is_absolute(), "Cannot broadcast on absolute subpath"
        path = self.path.joinpath(subpath)

        # Queue up event
        event = JournalEvent(
            path=path, guild=guild, content=content, attributes=attributes
        )
        self.router.queue.put_nowait(event)

    @property
    def history(self):
        return self.router.history
