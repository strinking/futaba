#
# cogs/optional/statbot/utils.py
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
Utilities for the Statbot cog.
"""

import struct
import hashlib


def int_hash(num):
    """
    The integer hashing algorithm used by Statbot to transform real user IDs.
    """

    data = struct.pack(">q", num)
    hashed = hashlib.sha512(data).digest()
    (result,) = struct.unpack(">q", hashed[24:32])
    return result
