#
# delayed.py
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
An asynchronous queue that takes in lower-priority discord.py API events
and sends them slowly over time. This prevents the bot from becoming
slowed down or gridlocked over long-running or mass operations.
"""

import asyncio
import inspect
import itertools
import logging

logger = logging.getLogger(__name__)


class DelayedQueue:
    __slots__ = ("config", "queue")

    def __init__(self, config):
        self.config = config
        self.queue = asyncio.Queue()

    def start(self, eventloop):
        eventloop.create_task(self.main_loop())

    def push(self, coro):
        assert inspect.iscoroutine(coro)
        self.queue.put_nowait(coro)

    async def main_loop(self):
        for i in itertools.count():
            coro = await self.queue.get()

            logger.debug("Got event #%d for processing", i)
            try:
                await coro
            except Exception as error:
                logger.error("Error awaiting delayed event", exc_info=error)

            if i % self.config.delay_chunk_size == 0:
                logger.debug(
                    "Sleeping for %.3f seconds until next delayed event",
                    self.config.delay_sleep,
                )
                await asyncio.sleep(self.config.delay_sleep)

    def __len__(self):
        return self.queue.qsize()
