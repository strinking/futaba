#
# config.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2021 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Loads config file from disk
"""

import re
from collections import namedtuple

import toml
from schema import Schema, And, Or

__all__ = ["Config", "load_config"]

ID_REGEX = re.compile(r"([0-9]{15,21})$")

ConfigSchema = Schema(
    {
        "bot": {
            "token": And(str, len),
            "prefix": str,
            "owners": [And(str, ID_REGEX.match)],
            "error-channel-id": Or(And(str, ID_REGEX.match), "0"),
        },
        "database": {"url": And(str, len)},
    }
)

Config = namedtuple(
    "Config",
    (
        "token",
        "prefix",
        "owner_ids",
        "error_channel_id",
        "database_url",
    ),
)


def load_config(file: str) -> Config:
    path = f"config/{file}"
    with open(path) as fh:
        config = toml.load(fh)

    ConfigSchema.validate(config)

    return Config(
        token=config["bot"]["token"],
        prefix=config["bot"]["prefix"],
        owner_ids=[int(id) for id in config["bot"]["owners"]],
        error_channel_id=int(config["bot"]["error-channel-id"]),
        database_url=config["database"]["url"],
    )
