#
# sql/models/navi.py
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
Model for storing tasks scheduled in navi, futaba's temporal assistant.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import namedtuple

from sqlalchemy import and_, cast, type_coerce
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Enum,
    Integer,
    Interval,
    JSON,
    String,
    Table,
)
from sqlalchemy import ForeignKey, Sequence
from sqlalchemy.sql import select

from futaba.enums import TaskType
from ..data import NaviTaskData
from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["NaviModel"]

ReminderInfo = namedtuple("ReminderInfo", ("id", "timestamp", "message"))


class NaviModel:
    __slots__ = ("sql", "tb_tasks")

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_tasks = Table(
            "tasks",
            meta,
            Column(
                "task_id",
                Integer,
                Sequence("task_seq", metadata=meta),
                primary_key=True,
            ),
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), nullable=True
            ),
            Column("user_id", BigInteger),
            Column("timestamp", DateTime),
            Column("recurrence", Interval, nullable=True),
            Column("type", Enum(TaskType)),
            Column("parameters", JSON),
        )

        register_hook("on_guild_leave", self.remove_all_tasks)

    def remove_all_tasks(self, guild):
        logger.info("Removing all tasks in guild '%s' (%d)", guild.name, guild.id)
        delet = self.tb_tasks.delete().where(self.tb_tasks.c.guild_id == guild.id)
        self.sql.execute(delet)

    def get_tasks(self):
        logger.info("Getting all tasks in the database")
        sel = select(
            [
                self.tb_tasks.c.task_id,
                self.tb_tasks.c.guild_id,
                self.tb_tasks.c.user_id,
                self.tb_tasks.c.timestamp,
                self.tb_tasks.c.recurrence,
                self.tb_tasks.c.type,
                self.tb_tasks.c.parameters,
            ]
        )
        result = self.sql.execute(sel)

        tasks = {}
        for (
            task_id,
            guild_id,
            user_id,
            timestamp,
            recurrence,
            task_type,
            parameters,
        ) in result.fetchall():
            logger.debug(
                "Got navi task %d: %s (%s) by user %d: %s (%s)",
                task_id,
                timestamp,
                recurrence,
                user_id,
                task_type,
                parameters,
            )
            tasks[task_id] = NaviTaskData(
                task_id, guild_id, user_id, timestamp, recurrence, task_type, parameters
            )
        return tasks

    def add_task(self, task):
        logger.info("Adding new task: %r", task)
        ins = self.tb_tasks.insert().values(
            guild_id=task.guild_id,
            user_id=task.causer.id,
            timestamp=task.timestamp,
            recurrence=task.recurrence,
            type=task.type,
            parameters=task.build_parameters(),
        )
        result = self.sql.execute(ins)
        (task.id,) = result.inserted_primary_key

    def remove_task(self, task):
        logger.info("Deleting task id %d", task.id)
        delet = self.tb_tasks.delete().where(self.tb_tasks.c.task_id == task.id)
        self.sql.execute(delet)

    def get_reminders(self, user):
        logger.info("Getting all reminders for user '%s' (%d)", user.name, user.id)
        sel = select(
            [
                self.tb_tasks.c.task_id,
                self.tb_tasks.c.timestamp,
                self.tb_tasks.c.parameters,
            ]
        ).where(
            and_(
                self.tb_tasks.c.user_id == user.id,
                cast(self.tb_tasks.c.parameters["metadata"]["type"], String)
                == type_coerce("reminder", JSON),
            )
        )
        result = self.sql.execute(sel)

        reminders = []
        for task_id, timestamp, parameters in result.fetchall():
            message = parameters["metadata"]["message"]
            logger.debug(
                "Got navi reminder %d: %s (message: %r)", task_id, timestamp, message
            )
            reminders.append(
                ReminderInfo(id=task_id, timestamp=timestamp, message=message)
            )
        return reminders
