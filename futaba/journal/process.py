#
# journal/process.py
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
Middleware for handling events before they are sent to all the listeners.
"""

from futaba.emojis import ICONS

__all__ = ["process_content"]


def process_content(content, attributes):
    """Modifies the content based on the passed attributes."""

    # Add icon
    icon = attributes.get("icon", None)
    if icon is not None:
        content = f"{ICONS[icon]} {content}"

    return content
