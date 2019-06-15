#
# cogs/optional/statbot/citizen.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from discord.ext import commands

from futaba.cogs.abc import AbstractCog
from futaba.exceptions import CommandFailed, SendHelp
from futaba.str_builder import StringBuilder

guild_settings = {
        247400063981191169: {
            "tracked-channels": [589312192902594576, 589312207301378048],
            "first-class-role": 589309608951021570,
            "min-msg": 5,

            }
        }

class Citizen(AbstractCog):

    def __init__(self, bot, sql):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/citizen")
        self.sql = sql

    def setup(self):
        new_guild_settings = {}
        for guild_id, settings in guild_settings.items():
            guild = self.bot.get_guild(guild_id)
            new_settings = {
                    **settings,
                    "first-class-role": guild.get_role(settings["first-class-role"]),
                    "tracked-channels": [guild.get_channel(id) for id in settings["tracked-channels"]],
                    }
            new_guild_settings[guild] = new_settings
        self.guild_settings = new_guild_settings

    @commands.group(name="citizen", aliases=["citi", "civ"])
    @commands.guild_only()
    async def citizen(self, ctx):
        """
        Manages member citizenship based on message count.
        """
        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @citizen.command(name="check", aliases=["c"])
    @commands.guild_only()
    async def check(self, ctx):
        """
        Reports a member's citizenship status.
        """
        guild_settings = self.guild_settings[ctx.guild]
        m, e, d = self.sql.message_count(ctx.guild, ctx.author, included_channels=guild_settings["tracked-channels"])
        existing_msgs = m - d
        if existing_msgs >= guild_settings["min-msg"]:
            await ctx.send(content="Thanks for your contributions!")
        else:
            await ctx.send(content="You'll get there soon!")
