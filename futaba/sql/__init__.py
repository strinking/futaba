#
# sql/__init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
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

from .settings import SettingsModel

logger = logging.getLogger(__name__)

__all__ = [
    'SqlHandler',
]

class SqlHandler:
    __slots__ = (
        'db',
        'conn',

        'settings',
    )

    def __init__(self, db_path: str):
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        logger.info("Connected to '%s'...", db_path)
        meta = MetaData(self.db)

        self.settings = SettingsModel(meta)

        meta.create_all(self.db)
        logger.info("Created all tables.")

    def transaction(self, trans_logger=logger):
        return Transaction(self.conn, trans_logger)
