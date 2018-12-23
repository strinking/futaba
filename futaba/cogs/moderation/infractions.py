#
# cogs/moderation/infractions.py
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
Collection of moderation commands that manage infractions and moderation history.
"""

import logging

from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Infractions"]


class Infractions(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/moderation/infraction")

    def setup(self):
        pass

    # TODO
