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

import asyncio
import logging
from queue import PriorityQueue

from .task import TASK_COMPLETE, AbstractNaviTask

"""
Module that contains the Navi scheduler, which manages all Navi tasks
and asynchronously executes them when their time is due.
"""

__all__ = ["NaviScheduler"]

logger = logging.getLogger(__name__)


class NaviScheduler:
    __slots__ = ("tasks",)

    def __init__(self):
        self.tasks = PriorityQueue()

    def add(self, task):
        self.tasks.put(task)

    async def main_loop(self):
        ...
