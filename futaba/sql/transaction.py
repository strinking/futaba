#
# sql/transaction.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

__all__ = [
    'Transaction',
]

class Transaction:
    __slots__ = (
        'conn',
        'logger',
        'trans',
        'ok',
    )

    def __init__(self, conn, logger):
        self.conn = conn
        self.logger = logger
        self.trans = None
        self.ok = True

    def __enter__(self):
        self.logger.debug("Starting transaction.")
        self.trans = self.conn.begin()
        return self

    def __exit__(self, type, value, traceback):
        if (type, value, traceback) == (None, None, None):
            self.logger.debug("Committing transaction.")
            self.trans.commit()
        else:
            self.logger.error("Exception occurred in 'with' scope!", exc_info=1)
            self.logger.debug("Rolling back transaction.")
            self.ok = False
            self.trans.rollback()

    async def __aenter__(self):
        self.__enter__()

    async def __aexit__(self, type, value, traceback):
        self.__exit__(type, value, traceback)

    def execute(self, *args, **kwargs):
        return self.conn.execute(*args, **kwargs)
