#
# sql.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging

from sqlalchemy import create_engine, MetaData
from sqlalchemy import Table

logger = logging.getLogger(__name__)

class SQLHandler:

    def __init__(self, db_path: str = 'sqlite:///futaba.db'):
        self.db = create_engine(db_path)
        self.conn = self.db.connect()
        logger.info(f'Connected to {db_path}')
        self.meta = MetaData(self.db)
        self.tables = {}

    def create_table(self, name, *args, **kwargs):
        try:
            return self.tables[name]
        except KeyError:
            table = Table(name, self.meta, *args, **kwargs)
            table.create(checkfirst=True)
            logger.debug(f'Table Created: {name}')
            self.tables[name] = table
            return table
