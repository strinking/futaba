#
# unicode.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging
import os
import re
import string
import unicodedata
from bisect import bisect
from urllib.request import urlretrieve

from futaba.str_builder import StringBuilder

logger = logging.getLogger(__name__)

__all__ = [
    "READABLE_CHAR_SET",
    "UNICODE_BLOCKS",
    "UNICODE_BLOCKS_FILENAME",
    "UNICODE_CATEGORY_NAME",
    "normalize_caseless",
    "unicode_block",
    "unicode_repr",
]

READABLE_CHAR_SET = frozenset(string.printable) - frozenset("\t\n\r\x0b\x0c")


# Adapted from https://gist.github.com/acdha/49a610089c2798db6fe2
def _load_unicode_blocks():
    if not os.path.exists(UNICODE_BLOCKS_FILENAME):
        logger.info(
            "Unicode blocks file '%s' does not exist, downloading...",
            UNICODE_BLOCKS_FILENAME,
        )
        urlretrieve(
            "https://unicode.org/Public/UNIDATA/Blocks.txt",
            filename=UNICODE_BLOCKS_FILENAME,
        )

    blocks = []
    with open(UNICODE_BLOCKS_FILENAME) as fh:
        content = fh.read()

    for start, end, block_name in re.findall(
        r"([0-9A-F]+)\.\.([0-9A-F]+);\ (\S.*\S)", content
    ):
        if block_name == "No_Block":
            continue

        blocks.append((int(start, 16), int(end, 16), block_name))
    return blocks


UNICODE_BLOCKS_FILENAME = "unidata-blocks.txt"
UNICODE_BLOCKS = _load_unicode_blocks()
UNICODE_BLOCK_STARTS = [block[0] for block in UNICODE_BLOCKS]

UNICODE_CATEGORY_NAME = {
    "Lu": "Letter, uppercase",
    "Ll": "Letter, lowercase",
    "Lt": "Letter, titlecase",
    "Lm": "Letter, modified",
    "Lo": "Letter, other",
    "Mn": "Mark, nonspacing",
    "Mc": "Mark, spacing combining",
    "Me": "Mark, enclosing",
    "Nd": "Number, decimal digit",
    "Nl": "Number, letter",
    "No": "Number, other",
    "Pc": "Punctuation, connector",
    "Pd": "Punctuation, dash",
    "Ps": "Punctuation, open",
    "Pe": "Punctuation, close",
    "Pi": "Punctuation, initial quote",
    "Pf": "Punctuation, final quote",
    "Po": "Punctuation, other",
    "Sm": "Symbol, mathematics",
    "Sc": "Symbol, currency",
    "Sk": "Symbol, modifier",
    "So": "Symbol, other",
    "Zs": "Separator, space",
    "Zl": "Separator, line",
    "Zp": "Separator, paragraph",
    "Cc": "Other, control",
    "Cf": "Other, format",
    "Cs": "Other, surrogate",
    "Co": "Other, private use",
    "Cn": "Other, not assigned",
}


def normalize_caseless(s):
    """
    Shifts the string into a uniform case (lowercase),
    but also accounting for unicode characters. Used
    for case-insenstive comparisons.
    """

    return unicodedata.normalize("NFKD", s.casefold())


def unicode_block(s):
    """Gets the name of the Unicode block that contains the given character."""

    codepoint = ord(s)
    index = bisect(UNICODE_BLOCK_STARTS, codepoint)
    try:
        _, stop, block = UNICODE_BLOCKS[index]
    except IndexError:
        return None

    return block if codepoint <= stop else None


def unicode_repr(s):
    """
    Similar to repr(), but always escapes characters that aren't "readable".
    That is, any characters not in READABLE_CHAR_SET.
    """

    result = StringBuilder('"')
    for ch in s:
        if ch == "\n":
            result.write("\\n")
        elif ch == "\t":
            result.write("\\t")
        elif ch == '"':
            result.write('\\"')
        elif ch in READABLE_CHAR_SET:
            result.write(ch)
        else:
            num = ord(ch)
            if num < 0x100:
                result.write(f"\\x{num:02x}")
            elif num < 0x10000:
                result.write(f"\\u{num:04x}")
            elif num < 0x100000000:
                result.write(f"\\U{num:08x}")
            else:
                raise ValueError(f"Character {ch!r} (ord {num:x}) too big for escaping")
    result.write('"')
    return str(result)
