#
# str_builder.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from io import BytesIO, StringIO

__all__ = ["StringBuilder"]


class StringBuilder:
    __slots__ = ("buffer", "sep")

    def __init__(self, initial="", sep=""):
        self.buffer = StringIO(initial)
        self.buffer.seek(len(initial))
        self.sep = sep

    def write(self, text):
        if self and self.sep:
            self.buffer.write(self.sep)

        self.buffer.write(str(text))

    def writeln(self, text="", endl="\n"):
        if self and self.sep:
            self.buffer.write(self.sep)

        self.buffer.writelines((str(text), endl))

    def clear(self):
        self.buffer.seek(0)
        self.buffer.truncate(0)

    def bytes(self):
        return str(self).encode("utf-8")

    def bytes_io(self):
        return BytesIO(self.bytes())

    def __str__(self):
        return self.buffer.getvalue()

    def __repr__(self):
        return f"<StringBuilder ({len(self)} chars) at 0x{id(self):08x}>"

    def __bool__(self):
        return bool(len(self))

    def __len__(self):
        return self.buffer.tell()
