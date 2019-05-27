#
# cogs/optional/statbot/sql.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Module for abstractly interfacing with Statbot's RDBMS.
"""

import logging

from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

__all__ = ["StatbotSqlHandler"]


class StatbotSqlHandler:
    __slots__ = ("db", "conn")

    def __init__(self, db_path: str):
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        logger.info("Connected to database...")
        logger.debug("DB URL is: %s", db_path)

    def __del__(self):
        self.conn.close()

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)
