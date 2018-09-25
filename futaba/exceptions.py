#
# exceptions.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

__all__ = [
    'CommandFailed',
    'SendHelp',
    'InvalidCommandContext',
    'InvalidConfigError',
]

class CommandFailed(RuntimeError):
    def __init__(self, content=None, embed=None, file=None):
        super().__init__()
        self.kwargs = {}

        if content is not None:
            self.kwargs['content'] = content
        if embed is not None:
            self.kwargs['embed'] = embed
        if file is not None:
            self.kwargs['file'] = file

class SendHelp(RuntimeError):
    def __init__(self, command):
        super().__init__()
        self.command = command

class InvalidCommandContext(RuntimeError):
    pass

class InvalidConfigError(RuntimeError):
    def __init__(self, message, config):
        super().__init__(message)
        self.config = config
