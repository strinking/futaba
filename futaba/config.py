#
# config.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
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

from futaba.exceptions import InvalidConfigError

__all__ = ["Configuration", "load_config"]

Configuration = namedtuple(
    "Configuration",
    (
        "token",
        "owner_ids",
        "default_prefix",
        "error_channel_id",
        "optional_cogs",
        "max_cleanup_messages",
        "delay_chunk_size",
        "delay_sleep",
        "anger_emoji_id",
        "python_emoji_id",
        "discord_py_emoji_id",
        "database_url",
    ),
)


def _get(config, field, path=None):
    if field not in config:
        if path is None:
            raise InvalidConfigError(
                f"No '{field}' section found in configuration.", config
            )
        else:
            raise InvalidConfigError(
                f"No '{path}.{field}' field found in configuration.", config
            )

    return config[field]


def load_config(path):
    with open(path) as fh:
        config = toml.load(fh)

    config_bot = _get(config, "bot")
    token = _get(config_bot, "token", "bot")
    prefix = _get(config_bot, "prefix", "bot")

    try:
        error_channel_id = int(_get(config_bot, "error-channel-id", "bot"))
    except ValueError:
        raise InvalidConfigError("Channel IDs must be integers", config)

    optional_cogs = _get(config_bot, "cogs", "bot")
    for key, value in optional_cogs.items():
        if not isinstance(value, bool):
            raise InvalidConfigError(f"Cog setting for {key} is not a boolean", config)

    try:
        owner_ids = [int(id) for id in _get(config_bot, "owners", "bot")]
    except ValueError:
        raise InvalidConfigError("Owner IDs must be integers", config)

    config_moderation = _get(config, "moderation")

    try:
        max_cleanup_messages = int(
            _get(config_moderation, "max-cleanup-messages", "moderation")
        )
        if max_cleanup_messages <= 0:
            raise ValueError
    except ValueError:
        raise InvalidConfigError(
            "Maximum cleanup messages value must be a positive integer", config
        )

    config_delay = _get(config, "delay")

    try:
        delay_chunk_size = int(_get(config_delay, "chunk-size", "delay"))
        delay_sleep = float(_get(config_delay, "sleep", "delay"))
    except ValueError:
        raise InvalidConfigError("Delay values must be numbers", config)

    config_emoji = _get(config, "emojis")

    try:
        anger_emoji_id = int(_get(config_emoji, "anger", "emojis"))
        python_emoji_id = int(_get(config_emoji, "python", "emojis"))
        discord_py_emoji_id = int(_get(config_emoji, "discordpy", "emojis"))
    except ValueError:
        raise InvalidConfigError("Emoji IDs must be integers", config)

    config_db = _get(config, "database")
    db_url = _get(config_db, "url", "database")

    return Configuration(
        token=token,
        owner_ids=owner_ids,
        default_prefix=prefix,
        error_channel_id=error_channel_id,
        optional_cogs=optional_cogs,
        max_cleanup_messages=max_cleanup_messages,
        delay_chunk_size=delay_chunk_size,
        delay_sleep=delay_sleep,
        anger_emoji_id=anger_emoji_id,
        python_emoji_id=python_emoji_id,
        discord_py_emoji_id=discord_py_emoji_id,
        database_url=db_url,
    )
