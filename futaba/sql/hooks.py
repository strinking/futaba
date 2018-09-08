#
# sql/hooks.py
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
Hooks that trigger on certain events to ensure database consistency.
'''

from collections import defaultdict
import logging

__all__ = [
    'run_hooks',
    'on_guild_join',
    'on_guild_leave',
]

_hooks = defaultdict(list)
logger = logging.getLogger(__name__)

def decorator_maker(name):
    def decorator(func):
        def hook(*args):
            logger.debug("Running hook: %s:%r", name, func)
            func(*args)
        _hooks[name].append(hook)
        return func
    return decorator

def run_hooks(sql, name, *args):
    logger.info("Running hooks for '%s'...", name)
    with sql.transaction():
        for hook in _hooks[name]:
            try:
                hook(*args)
            except Exception as error:
                logger.error("Error running hook %r!", hook, exc_info=error)
    logger.debug("Finished '%s' hooks.", name)

on_guild_join = decorator_maker('on_guild_join')
on_guild_leave = decorator_maker('on_guild_leave')
