#
# sql/data/navi.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#


class NaviTaskData:
    __slots__ = (
        "id",
        "guild_id",
        "user_id",
        "timestamp",
        "recurrence",
        "task_type",
        "parameters",
    )

    def __init__(
        self, id, guild_id, user_id, timestamp, recurrence, task_type, parameters
    ):
        self.id = id
        self.guild_id = guild_id
        self.user_id = user_id
        self.timestamp = timestamp
        self.recurrence = recurrence
        self.task_type = task_type
        self.parameters = parameters
