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

'''
Module for abstractly interfacing with the RDBMS.
'''

import logging

from sqlalchemy import create_engine, MetaData

from .models import FilterModel, GuildsModel, JournalModel, SettingsModel, WelcomeModel
from .transaction import Transaction

logger = logging.getLogger(__name__)

__all__ = [
    'SqlHandler',
]

class SqlHandler:
    __slots__ = (
        'db',
        'conn',
        'trans',

        'filter',
        'guilds',
        'journal',
        'settings',
        'welcome',
    )

    def __init__(self, db_path: str):
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        self.trans = None
        logger.info("Connected to '%s'...", db_path)
        meta = MetaData(self.db)

        self.filter = FilterModel(self, meta)
        self.guilds = GuildsModel(self, meta)
        self.journal = JournalModel(self, meta)
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
