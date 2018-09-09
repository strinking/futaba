#
# journal/__init__.py
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
Module for defining components of the journaling system.
This file instantiates a single, global router, and provides
Broadcaster and Listener classes that rely on it.
'''

from functools import partial

from .broadcaster import Broadcaster as UnboundBroadcaster
from .listener import Listener as UnboundListener
from .router import Router

__all__ = [
    'JOURNAL',
    'Broadcaster',
    'Listener',
    'Router',
    'UnboundBroadcaster',
    'UnboundListener',
]

JOURNAL = Router()
Broadcaster = partial(UnboundBroadcaster, JOURNAL)
Listener = partial(UnboundListener, JOURNAL)
