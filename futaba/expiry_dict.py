#
# expiry_dict.py
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
Collection that has keys which expire.
"""

from datetime import datetime


class ExpiryDict:
    __slots__ = ("items", "expire_time")

    def __init__(self, expire_time):
        self.items = {}
        self.expire_time = expire_time

    def prune(self):
        now = datetime.now()

        for key in tuple(self.items.keys()):
            expires_at, _ = self.items[key]

            if now > expires_at:
                del self.items[key]

    def __getitem__(self, key):
        self.prune()
        _, value = self.items[key]
        return value

    def __setitem__(self, key, value):
        self.prune()
        expires_at = datetime.now() + self.expire_time
        self.items[key] = expires_at, value

    def __delitem__(self, key):
        del self.items[key]

    def __contains__(self, key):
        return key in self.items

    def keys(self):
        return self.items.keys()
