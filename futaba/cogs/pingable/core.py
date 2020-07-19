#
# cogs/pingable/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Cog for pingable helper roles
"""

import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands
from futaba.permissions import mod_perm
from futaba.exceptions import CommandFailed
from futaba.utils import fancy_timedelta
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Pingable"]


class Pingable(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/pingable")
        self.cooldowns = {}

    def setup(self):
        pass

    @commands.command(name="pinghelpers", aliases=["helpme", "pinghelp"])
    async def pinghelpers(self, ctx):
        """Pings helpers if used in the respective channel"""

        cooldown_time = self.bot.config.helper_ping_cooldown

        logger.info(
            "User '%s' (%d) is pinging the helper role in channel '%s' in guild '%s' (%d)",
            ctx.author,
            ctx.author.mention,
            ctx.channel,
            ctx.guild,
            ctx.guild.id,
        )
        pingable_channels = self.bot.sql.roles.get_pingable_role_channels(ctx.guild)
        # this will return an empty list if there is nothing.
        channel_role = [
            (channel, role)
            for channel, role in pingable_channels
            if channel == ctx.channel
        ]

        if not channel_role:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.set_author(name="Failed to ping helper role.")
            embed.description = f"There is no helper role set for this channel."
            raise CommandFailed(embed=embed)

        channel_user = (ctx.channel.id, ctx.author.id)
        cooldown = self.cooldowns.get(channel_user)

        if mod_perm(ctx) or not cooldown or cooldown <= datetime.now():
            self.cooldowns[channel_user] = datetime.now() + timedelta(
                seconds=cooldown_time
            )

            # This will loop over the dictionary and remove expired entries.
            key_list = list(self.cooldowns.keys())
            for k in key_list:
                if self.cooldowns[k] < datetime.now():
                    del self.cooldowns[k]

            # channel[0] will be the first tuple in the list. there will only be one, since the
            # channel's id is a primary key (tb_pingable_role_channel in roles.py). channel[0][1] is the role.
            await ctx.send(
                f"{channel_role[0][1].mention}, {ctx.author.mention} needs help."
            )

        elif cooldown > datetime.now():
            # convert deltatime into string: Hh, Mm, Ss
            time_remaining = cooldown - datetime.now()

            embed = discord.Embed(colour=discord.Colour.red())
            embed.set_author(name="Failed to ping helper role.")
            embed.description = f"You can ping the helper role for this channel again in {fancy_timedelta(time_remaining)}"
            raise CommandFailed(embed=embed)
