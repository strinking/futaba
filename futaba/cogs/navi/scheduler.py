#
# cogs/navi/scheduler.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Module that contains the Navi scheduler, which manages all Navi tasks
and asynchronously executes them when their time is due.
"""

import asyncio
import logging
from datetime import datetime

from .task import TASK_COMPLETE

__all__ = ["NaviScheduler"]

logger = logging.getLogger(__name__)


class NaviScheduler:
    __slots__ = ("tasks",)

    def __init__(self):
        self.tasks = asyncio.PriorityQueue()

    def add(self, task):
        self.tasks.put_nowait(task)

    async def main_loop(self):
        logger.info("Starting Navi scheduler's main loop...")
        while True:
            logger.debug("Waiting for new task to queue...")
            task = await self.tasks.get()
            due_next = task.due_next()
            if due_next is TASK_COMPLETE:
                logger.debug("Task is complete, skip it")
                continue

            delay = (datetime.utcnow() - due_next).total_seconds()
            logger.debug("Got task: %r. Will wait %.4f seconds for it", task, delay)
            if delay > 0.0:
                await asyncio.sleep(delay)
            await task.execute()
