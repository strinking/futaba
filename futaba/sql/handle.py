#
# sql/handle.py
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
Module for abstractly interfacing with the RDBMS.
"""

import logging

from sqlalchemy import create_engine, MetaData

from .models import (
    AliasHistoryModel,
    FilterModel,
    GuildsModel,
    JournalModel,
    ModerationModel,
    NaviModel,
    RolesModel,
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
        "moderation",
        "navi",
        "roles",
        "settings",
        "welcome",
    )

    def __init__(self, db_path: str, max_delete_messages=500):
        self.max_delete_messages = max_delete_messages
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        self.trans = None
        logger.info("Connected to database...")
        meta = MetaData(self.db)

        self.alias = AliasHistoryModel(self, meta)
        self.filter = FilterModel(self, meta)
        self.guilds = GuildsModel(self, meta)
        self.journal = JournalModel(self, meta)
        self.moderation = ModerationModel(self, meta)
        self.navi = NaviModel(self, meta)
        self.roles = RolesModel(self, meta)
        self.settings = SettingsModel(self, meta)
        self.welcome = WelcomeModel(self, meta)

        meta.create_all(self.db)
        logger.info("Created all tables.")

    def __del__(self):
        self.conn.close()

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)

    def transaction(self, trans_logger=logger):
        if self.trans is None:
            self.trans = Transaction(self, self.conn, trans_logger)

        return self.trans
