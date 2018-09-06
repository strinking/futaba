#
# __init__.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
futaba - A Discord Mod bot for the Programming server
'''

from . import client, config, enums, permissions, utils

__all__ = [
    '__version__',
    'client',
    'config',
    'enums',
    'permissions',
    'utils',
]

__version__ = '0.0.3'
