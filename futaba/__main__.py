#
# __main__.py
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
Used to start the bot allows the command to take arguments
"""

import logging
import argparse
import sys

import schema
from toml import TomlDecodeError

from futaba import client
from futaba.config import load_config

# Logging Constants
LOG_FILE = "logs/futaba.log"
LOG_FILE_MODE = "w"
LOG_FORMAT = "[%(levelname)s] %(asctime)s %(name)s: %(message)s"
LOG_DATE_FORMAT = "[%Y/%m/%d %H:%M:%S]"

if __name__ == "__main__":
    # Parse arguments
    argparser = argparse.ArgumentParser(description="A Discord Mod bot for the Programming server")
    argparser.add_argument(
        "-q",
        "--quiet",
        "--no-stdout",
        dest="stdout",
        action="store_false",
        help="Don't output to standard out.",
    )
    argparser.add_argument(
        "-d",
        "--debug",
        dest="debug",
        action="store_true",
        help="Set logging level to debug for the bot.",
    )
    argparser.add_argument(
        "-D",
        "--discord",
        dest="discord_log",
        action="store_true",
        help="Adds the Discord logger to the log file.",
    )
    argparser.add_argument("config_file", help="Specify a configuration file to use. Keep it secret!")
    args = argparser.parse_args()

    # Set up logging
    log_fmtr = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    log_handler = logging.FileHandler(filename=LOG_FILE, encoding="utf-8", mode=LOG_FILE_MODE)
    log_handler.setFormatter(log_fmtr)

    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = logging.getLogger(__package__)
    logger.setLevel(level=log_level)
    logger.addHandler(log_handler)

    # Create discord logger
    if args.discord_log:
        discord_logger = logging.getLogger("discord")
        discord_logger.setLevel(level=logging.INFO)
        discord_logger.addHandler(log_handler)

    # Create std output logger
    if args.stdout:
        std_logger = logging.getLogger(__package__)
        std_logger.setLevel(level=logging.DEBUG)
        std_logger.addHandler(log_handler)

        log_stdout = logging.StreamHandler(sys.stdout)
        log_stdout.setFormatter(log_fmtr)
        std_logger.addHandler(log_stdout)
        if args.discord_log:
            discord_logger.addHandler(log_stdout)

    # Load config
    try:
        config = load_config(args.config_file)
    except (TomlDecodeError, IOError) as error:
        logger.error("Unable to read config file.", exc_info=error)
        sys.exit(1)
    except schema.SchemaError as error:
        logger.error("Error processing config file.", exc_info=error)
        sys.exit(1)

    # Start bot
    logger.info("Starting Bot...")
    bot = client.Bot(config)
    bot.run_with_token()
