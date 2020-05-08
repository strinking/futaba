#
# exceptions.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from discord.ext.commands import CommandError

__all__ = ["CommandFailed", "ManualCheckFailure", "SendHelp", "InvalidCommandContext"]


class SendOnError(CommandError):
    def __init__(self, content=None, embed=None, file=None):
        super().__init__()
        self.kwargs = {}

        if content is not None:
            self.kwargs["content"] = content
        if embed is not None:
            self.kwargs["embed"] = embed
        if file is not None:
            self.kwargs["file"] = file


class CommandFailed(SendOnError):
    pass


class ManualCheckFailure(SendOnError):
    pass


class SendHelp(CommandError):
    pass


class InvalidCommandContext(CommandError):
    pass
