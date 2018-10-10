#
# sql/handle.py
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
Module for abstractly interfacing with the RDBMS.
"""

import logging

from sqlalchemy import create_engine, MetaData

from .models import (
    AliasHistoryModel,
    FilterModel,
    GuildsModel,
    JournalModel,
    SelfAssignableRolesModel,
    SettingsModel,
    WelcomeModel,
)
from .transaction import Transaction

logger = logging.getLogger(__name__)

__all__ = ["SqlHandler"]


class SqlHandler:
    __slots__ = (
        "db",
        "conn",
        "trans",
        "max_delete_messages",
        "alias",
        "filter",
        "guilds",
        "journal",
        "roles",
        "settings",
        "welcome",
    )

    def __init__(self, db_path: str, max_delete_messages=500):
        self.max_delete_messages = max_delete_messages
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        self.trans = None
        logger.info("Connected to '%s'...", db_path)
        meta = MetaData(self.db)

        self.alias = AliasHistoryModel(self, meta)
        self.filter = FilterModel(self, meta)
        self.guilds = GuildsModel(self, meta)
        self.journal = JournalModel(self, meta)
        self.roles = SelfAssignableRolesModel(self, meta)
        self.settings = SettingsModel(self, meta)
        self.welcome = WelcomeModel(self, meta)

        meta.create_all(self.db)
        logger.info("Created all tables.")

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)

    def transaction(self, trans_logger=logger):
        assert self.trans is None, "Already in a transaction"
        self.trans = Transaction(self, self.conn, trans_logger)
        return self.trans
