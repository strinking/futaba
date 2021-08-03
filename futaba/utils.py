#
# utils.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2021 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""Contains utitiy functions used by the bot"""


def plural(num: int) -> str:
    """ Gets the English plural ending for an ordinal number. """

    return "" if num == 1 else "s"
