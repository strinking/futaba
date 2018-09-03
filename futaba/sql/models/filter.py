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

import functools
import logging
from enum import Enum, unique

from sqlalchemy import and_, or_
from sqlalchemy import BigInteger, Column, Enum, Table, Unicode
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.sql import select

from cogs.filter import FilterType
from utils import normalize_caseless

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = [
    'LocationType',
    'FilterModel',
]

@unique
class LocationType(Enum):
    CHANNEL = 'channel'
    GUILD = 'guild'

    @staticmethod
    def of(location):
        if instanceof(location, discord.Guild):
            return LocationType.GUILD
        elif instanceof(location, discord.TextChannel):
            return LocationType.CHANNEL
        else:
            return TypeError(r"No location type for %r")

class FilterModel:
    __slots__ = (
        'sql',
        'tb_filters',
        'filter_cache',
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_filters = Table('filters', meta,
                Column('location_id', BigInteger, primary_key=True),
                Column('location_type', Enum(LocationType)),
                Column('filter_type', Enum(FilterType)),
                Column('text', Unicode),
                UniqueConstraint('location_id', 'text', name='uq_filter'))
        self.filter_cache = {}

    def filter_cache_delete(self, location, text):
        for filter_type in FilterType:
            self.filter_cache[location][filter_type].remove(text)

    def get_filters(self, location):
        logger.debug("Getting filters for location '%s' (%d)", location.name, location.id)
        if location in self.filter_cache:
            logger.trace("Filter list was found in cache, returning")
            return self.filter_cache[location]

        sel = select([self.tb_filters.c.type, self.tb_filters.c.text]) \
                .where(self.tb_filters.c.location_id == location.id) \
                .order_by(self.tb_filters.c.type)
        result = self.sql.execute(sel)

        filters = {filter_type: set() for filter_type in FilterType}
        for filter_type, text in result.fetchmany():
            filters[filter_type].add(text)

        self.filter_cache[location] = filters
        return filters

    def add_filter(self, location, filter_type, text):
        logger.info("Adding text %r to filter, level '%s'", text, type)

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
            self.filter_cache[filter_type].append(text)
        except sqlalchemy.exc.IntegrityError:
            raise ValueError("This filter already exists")

    def update_filter(self, location, filter_type, text):
        logger.info("Updating filter %r to level '%s'", text, filter_type)

        text = normalize_caseless(text)
        upd = self.tb_filters \
                .update() \
                .where(and_(
                    self.tb_filters.c.location_id == location.id,
                    self.tb_filters.c.location_type == LocationType.of(location),
                    self.tb_filters.c.text == text,
                ))
        self.sql.execute(upd)
        self.filter_cache_delete(location, text)
        self.filter_cache[location][type].add(text)

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
        self.filter_cache_delete(location, text)
        assert result.rowcount in (0, 1)
        return bool(result.rowcount)
