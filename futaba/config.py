#
# config.py
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
Loads configuration files from disk
"""

from collections import namedtuple

import toml
from schema import Schema, And, Or

from futaba.converters import ID_REGEX

__all__ = ["Configuration", "load_config"]


# Helper function to check that the value is greater than zero
def _check_gtz(type):
    def wrapper(value):
        try:
            value = type(value)
        except ValueError:
            return False
        return value > 0

    return wrapper


ConfigurationSchema = Schema(
    {
        "bot": {
            "token": And(str, len),
            "owners": [And(str, ID_REGEX.match)],
            "prefix": str,
            "error-channel-id": Or(And(str, ID_REGEX.match), "0"),
        },
        "cogs": {"example": object, "statbot": object},
        "moderation": {
            "max-cleanup-messages": And(str, _check_gtz(int)),
            "ping-cooldown": And(str, _check_gtz(int)),
        },
        "delay": {
            "chunk-size": And(str, _check_gtz(int)),
            "sleep": And(str, _check_gtz(float)),
        },
        "emojis": {
            "anger": Or(And(str, ID_REGEX.match), "0"),
            "python": Or(And(str, ID_REGEX.match), "0"),
            "discordpy": Or(And(str, ID_REGEX.match), "0"),
        },
        "database": {"url": And(str, len)},
        "jwt": {"secret": And(str, len)},
    }
)

Configuration = namedtuple(
    "Configuration",
    (
        "token",
        "owner_ids",
        "default_prefix",
        "error_channel_id",
        "optional_cogs",
        "max_cleanup_messages",
        "helper_ping_cooldown",
        "delay_chunk_size",
        "delay_sleep",
        "anger_emoji_id",
        "python_emoji_id",
        "discord_py_emoji_id",
        "database_url",
        "jwt_secret",
    ),
)


def load_config(path):
    with open(path) as fh:
        config = toml.load(fh)

    ConfigurationSchema.validate(config)

    return Configuration(
        token=config["bot"]["token"],
        owner_ids=[int(id) for id in config["bot"]["owners"]],
        default_prefix=config["bot"]["prefix"],
        error_channel_id=int(config["bot"]["error-channel-id"]),
        optional_cogs=config["cogs"],
        max_cleanup_messages=int(config["moderation"]["max-cleanup-messages"]),
        helper_ping_cooldown=int(config["moderation"]["ping-cooldown"]),
        delay_chunk_size=int(config["delay"]["chunk-size"]),
        delay_sleep=float(config["delay"]["sleep"]),
        anger_emoji_id=int(config["emojis"]["anger"]),
        python_emoji_id=int(config["emojis"]["python"]),
        discord_py_emoji_id=int(config["emojis"]["discordpy"]),
        database_url=config["database"]["url"],
        jwt_secret=config["jwt"]["secret"],
    )
