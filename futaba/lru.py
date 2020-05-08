#
# lru.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from collections import OrderedDict
from collections.abc import MutableMapping


class LruCache(MutableMapping):
    def __init__(self, max_size=None):
        self.store = OrderedDict()
        self.max_size = max_size

    def __getitem__(self, key):
        obj = self.store.pop(key)
        self.store[key] = obj
        return obj

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            if callable(default):
                return default()
            else:
                return default

    def get_or_put(self, key, default):
        try:
            return self[key]
        except KeyError:
            item = default() if callable(default) else default
            self[key] = item
            return item

    def __setitem__(self, key, value):
        self.store.pop(key, None)
        self.store[key] = value

        while len(self) > self.max_size:
            self.store.popitem(last=False)

    def __delitem__(self, key):
        del self.store[key]

    def __contains__(self, key):
        return key in self.store

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)
