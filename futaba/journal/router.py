#
# journal/router.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
from collections import defaultdict
from itertools import chain

logger = logging.getLogger(__name__)

__all__ = [
    'Router',
]

class Router:
    __slots__ = (
        'paths',
        'queue',
    )

    def __init__(self):
        self.paths = defaultdict(list)
        self.queue = asyncio.Queue()

    def start(self, eventloop):
        logger.info("Start journal event processing task")
        eventloop.create_task(self.process_events())

    def register(self, listener):
        logger.info("Registering %r on '%s'", listener, listener.path)
        self.paths[listener.path].append(listener)

    async def process_events(self):
        events = []

        while True:
            logger.debug("Waiting for new journal event")
            event_path, content, attributes = await self.queue.get()
            logger.info("Got journal event on %s: '%s' %s", event_path, content, attributes)

            # Add events for this path
            for path in chain((event_path,), event_path.parents):
                for listener in self.paths[path]:
                    if listener.check(path, content, attributes):
                        events.append(listener.handle(path, content, attributes))

            # Run all the event handlers
            await asyncio.gather(*events)
            events.clear()
