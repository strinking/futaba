#
# __main__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# mawabot is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Used to start the bot allows the command to take arguments
'''

import logging
import argparse
import sys

import yaml

from . import client

LOG_FILE = 'futaba.log'
LOG_FILE_MODE = 'w'
LOG_FORMAT = '[%(levelname)s] %(asctime)s %(name)s: %(message)s'
LOG_DATE_FORMAT = '[%d/%m/%Y %H:%M]'

if __name__ == '__main__':
    # Parse arguments
    argparser = argparse.ArgumentParser(description='maware\'s self-bot')
    argparser.add_argument('-q', '--quiet', '--no-stdout',
                           dest='stdout', action='store_false',
                           help="Don't output to standard out.")
    argparser.add_argument('-d', '--debug',
                           dest='debug', action='store_true',
                           help="Set logging level to debug for the selfbot.")
    argparser.add_argument('-D', '--discord',
                           dest='dis_log', action='store_true',
                           help="Adds the Discord logger to the log file.")
    argparser.add_argument('config_file',
                           help="Specify a configuration file to use. Keep it secret!")
    args = argparser.parse_args()

    # Set up logging
    log_fmtr = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    log_hndl = logging.FileHandler(filename=LOG_FILE,
                                   encoding='utf-8', mode=LOG_FILE_MODE)
    log_hndl.setFormatter(log_fmtr)

    log_level = logging.DEBUG if args.debug else logging.INFO

    logger = logging.getLogger(__package__)
    logger.setLevel(level=log_level)
    logger.addHandler(log_hndl)

    if args.dis_log:
        dis_logger = logging.getLogger('discord')
        dis_logger.setLevel(level=logging.INFO)
        dis_logger.addHandler(log_hndl)

    if args.stdout:
        log_hndl = logging.StreamHandler(sys.stdout)
        log_hndl.setFormatter(log_fmtr)
        logger.addHandler(log_hndl)
        if args.dis_log:
            dis_logger.addHandler(log_hndl)

    try:
        # Load config
        with open(args.config_file, 'r') as fh:
            config = yaml.safe_load(fh)
    except (yaml.YAMLError, IOError) as err:
        logger.error("Configuration file was invalid.")
        exit(1)

    # Open and run client
    logger.info("Starting bot...")
    bot = client.Bot(config)
    bot.run_with_token()
