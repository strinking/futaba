#
# sql/data/journal.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from collections import namedtuple

ConfiguredJournalOutput = namedtuple(
    "ConfiguredJournalOutput", ("sink", "path", "settings")
)


class JournalOutputData:
    __slots__ = ("recursive",)

    def __init__(self, recursive):
        self.recursive = recursive
