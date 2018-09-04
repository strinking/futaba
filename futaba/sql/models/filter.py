#
# sql/filter.py
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
Has the model for persisting filter settings.
'''

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging
from collections import defaultdict

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Enum, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from futaba.enums import LocationType, FilterType
from futaba.utils import normalize_caseless

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'FilterModel',
]

class FilterModel:
    __slots__ = (
        'sql',
        'tb_filters',
        'filter_cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_filters = Table('filters', meta,
                Column('location_id', BigInteger),
                Column('location_type', Enum(LocationType)),
                Column('filter_type', Enum(FilterType)),
                Column('text', Unicode),
                UniqueConstraint('location_id', 'location_type', 'filter_type', 'text', name='uq_filter'))
        self.filter_cache = defaultdict(dict)

    def get_filters(self, location):
        logger.debug("Getting filters for location '%s' (%d)", location.name, location.id)
        if location in self.filter_cache:
            logger.debug("Filter list was found in cache, returning")
            return self.filter_cache[location]

        sel = select([self.tb_filters.c.filter_type, self.tb_filters.c.text]) \
                .where(and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                )) \
                .order_by(self.tb_filters.c.filter_type)
        result = self.sql.execute(sel)

        filters = {text: filter_type for (filter_type, text) in result.fetchmany()}
        self.filter_cache[location] = filters
        return filters

    def add_filter(self, location, filter_type, text):
        logger.info("Adding text %r to filter, level '%s'", text, filter_type.value)

        text = normalize_caseless(text)
        ins = self.tb_filters \
                .insert() \
                .values(
                    location_id=location.id,
                    location_type=LocationType.of(location),
                    filter_type=filter_type,
                    text=text,
                )

        try:
            self.sql.execute(ins)
            self.filter_cache[location][text] = filter_type
        except IntegrityError:
            raise ValueError("This filter already exists")

    def update_filter(self, location, filter_type, text):
        logger.info("Updating filter %r to level '%s'", text, filter_type.value)

        text = normalize_caseless(text)
        upd = self.tb_filters \
                .update() \
                .where(and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                    self.tb_filters.c.text == text,
                ))
        print(upd)
        self.sql.execute(upd)
        del self.filter_cache[location][text]
        self.filter_cache[location][text] = filter_type

    def delete_filter(self, location, text):
        logger.info("Deleting filter %r", text)

        delet = self.tb_filters \
                .delete() \
                .where(and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                    self.tb_filters.c.text == text,
                ))
        result = self.sql.execute(delet)
        del self.filter_cache[location][text]
        assert result.rowcount in (0, 1), "Only one matching filter"
        return bool(result.rowcount)
