#
# cogs/abc.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Emmie Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

""" Abstract base class for all cog classes. """

from abc import abstractmethod

from discord.ext import commands
from discord.ext.commands.bot import Bot


class AbstractCog(commands.Cog):
    __slots__ = ("bot",)

    def __init__(self, bot: Bot):
        self.bot = bot

    @abstractmethod
    def setup(self):
        pass
