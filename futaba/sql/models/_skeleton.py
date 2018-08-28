#
# sql/_FILENAME_HERE_.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

# XXX _REMOVE_ME_
# pylint: disable=unused-import

import functools
import logging

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

'''
_DESCRIPTION_HERE_
'''

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)
