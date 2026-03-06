#
# cogs/optional/simplewriter/words/words.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import os

__all__ = ["core_words_list"]

core_words_list = []
core_words_list_path = os.path.join(os.path.dirname(__file__), "core_words_list.txt")

with open(core_words_list_path, "r") as f:
    core_words_list = f.read().split(",")
