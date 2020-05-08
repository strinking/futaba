#
# sql/data/filter.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#


class FilterSettingsData:
    __slots__ = ("bot_immune", "manage_messages_immune", "reupload")

    def __init__(self):
        self.bot_immune = False
        self.manage_messages_immune = True
        self.reupload = True

    def updated(self, field, value=None):
        """
        Sets 'field' if 'value' is not None. Returns the current value of 'field'.
        Useful for getting an excluded field, and updating the storage object too.
        """

        if value is not None:
            setattr(self, field, value)

        return getattr(self, field)
