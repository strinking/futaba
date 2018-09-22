#
# str_builder.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from io import StringIO

__all__ = [
    'StringBuilder',
]

class StringBuilder:
    __slots__ = (
        'buffer',
    )

    def __init__(self, initial=''):
        self.buffer = StringIO(initial)

    def write(self, text):
        self.buffer.write(str(text))

    def writeln(self, text):
        self.buffer.writelines((str(text), '\n'))

    def clear(self):
        self.buffer.seek(0)
        self.buffer.truncate(0)

    def __str__(self):
        return self.buffer.getvalue()

    def __bool__(self):
        return bool(len(self))

    def __len__(self):
        return self.buffer.tell()
