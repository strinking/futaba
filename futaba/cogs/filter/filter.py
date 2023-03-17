#
# cogs/filter/filter.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

# pylint: disable=no-member
import logging
import re
import sre_parse
import sre_compile

from collections.abc import Iterable

from confusable_homoglyphs import confusables

from futaba.str_builder import StringBuilder

logger = logging.getLogger(__name__)

__all__ = ["UNICODE_SPACES_REGEX", "Filter"]

UNICODE_SPACES_REGEX = re.compile(
    "".join(
        (
            "[",
            "\u0020\u00a0\u1680",
            "\u180e\u2000\u2001",
            "\u2002\u2003\u2004",
            "\u2005\u2006\u2006",
            "\u2007\u2008\u2009",
            "\u200a\u200b\u202f",
            "\u205f\u3000\ufeff",
            "]",
        )
    )
)


class SyntheticPattern:
    __slots__ = ("compiled", "pattern")

    def __init__(self, compiled, pattern):
        self.compiled = compiled
        self.pattern = pattern

    def __getattr__(self, item):
        return getattr(self.compiled, item)


class Filter:
    __slots__ = ("text", "regex")

    def __init__(self, text):
        logger.info("Creating filter regular expression from %r", text)
        if text.startswith("regex:") and len(text) > 6:
            # Build a general regular expression, de-confusifying LITERALs
            pattern = text[6:].encode()
            regex_ast = sre_parse.parse(pattern)
            regex_ast = Filter.convert_raw_regex_ast(regex_ast)
            compiled = sre_compile.compile(regex_ast, re.IGNORECASE)
            compiled = SyntheticPattern(compiled, "<synthetic regular expression>")
        elif text.startswith("raw-regex:") and len(text) > 10:
            pattern = text[10:].encode()
            compiled = re.compile(pattern, re.IGNORECASE)
        else:
            groups = confusables.is_confusable(text, greedy=True)
            if groups:
                pattern = Filter.build_regex(text, groups)
            else:
                pattern = re.escape(text)
            compiled = re.compile(pattern, re.IGNORECASE)

        logger.debug("Generated pattern: %r", compiled.pattern)

        self.text = text
        self.regex = compiled

    @staticmethod
    def build_regex(text, groups):
        # Build similar character tree
        chars = {}
        pattern = StringBuilder()
        for group in groups:
            pattern.write("[")
            char = group["character"]
            pattern.write(re.escape(char))
            for homoglyph in group["homoglyphs"]:
                pattern.write(re.escape(homoglyph["c"]))
            pattern.write("]")
            chars[char] = str(pattern)
            pattern.clear()

        # Create pattern
        for char in text:
            pattern.write(chars.get(char, char))

        return str(pattern)

    @staticmethod
    def generate_confusable_literals(confusable: chr) -> list:
        # Generates list of confusable homoglyphs LITERALs based on input
        # character, includes input character

        groups = confusables.is_confusable(confusable, greedy=True)

        confusable_literals = [(sre_parse.LITERAL, ord(confusable))]

        if not groups:
            return confusable_literals

        # Append confusables to list as LITERALs
        for homoglyph in groups[0]["homoglyphs"]:
            confusable_literals += [
                (re.sre_parse.LITERAL, ord(char)) for char in homoglyph["c"]
            ]

        return confusable_literals

    @staticmethod
    def convert_raw_regex_ast(regex_ast: Iterable):
        for index, value in enumerate(regex_ast):
            if isinstance(value, tuple):
                # (TOKEN_NAME, TOKEN_VALUE) likely
                (
                    token_name,
                    token_value,
                    *_,
                ) = value
                if token_name == sre_parse.IN:
                    # (IN, [ (LITERAL, ord) ... ])
                    # sets cannot be nested, need to insert confusables in place
                    confusable_literals = []
                    for literal in token_value:
                        confusable_literals += Filter.generate_confusable_literals(
                            chr(literal[1])
                        )
                    token_value += confusable_literals
                if token_name == sre_parse.LITERAL:
                    # (LITERAL, ord), replace with set
                    confusable_literals = Filter.generate_confusable_literals(
                        chr(token_value)
                    )
                    regex_ast[index] = (sre_parse.IN, confusable_literals)
                else:
                    # Miscellaneous token, might contain more tokens
                    # Recurse and overwrite...
                    regex_ast[index] = tuple(Filter.convert_raw_regex_ast(list(value)))
            elif isinstance(value, sre_parse.SubPattern):
                regex_ast[index] = Filter.convert_raw_regex_ast(value)

        return regex_ast

    def matches(self, content):
        contents = (content, UNICODE_SPACES_REGEX.sub("", content))

        return bool(any(map(self.regex.search, contents)))

    def __hash__(self):
        return hash(self.text) ^ 0x2C6F024ED28

    def __eq__(self, other):
        return (
            isinstance(self, Filter)
            and isinstance(other, Filter)
            and self.text == other.text
        )
