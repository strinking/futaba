#
# converters/utils.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import re

__all__ = ["ID_REGEX"]

ID_REGEX = re.compile(r"([0-9]{15,21})$")
DUAL_ID_REGEX = re.compile(r"([0-9]{15,21})-([0-9]{15,21})$")
