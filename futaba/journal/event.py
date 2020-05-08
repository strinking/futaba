#
# journal/event.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from futaba.dict_convert import named_dict, to_dict


class JournalEvent:
    __slots__ = ("path", "guild", "content", "attributes")

    def __init__(self, *, path, guild, content, attributes):
        self.path = path
        self.guild = guild
        self.content = content
        self.attributes = attributes

    def to_dict(self):
        return {
            "path": str(self.path),
            "guild": named_dict(self.guild),
            "content": self.content,
            "attributes": {
                key: to_dict(value) for key, value in self.attributes.items()
            },
        }
