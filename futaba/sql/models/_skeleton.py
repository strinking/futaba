#
# sql/models/_FILENAME_HERE_.py
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
_DESCRIPTION_HERE_
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["_SKELETON_Model"]


class _SKELETON_Model:
    pass
