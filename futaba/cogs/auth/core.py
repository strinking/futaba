#
# cogs/auth/core.py
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
Cog for authentication schemes and token generation
"""

import logging
from datetime import datetime
from jose import jwt

import discord
from discord.ext import commands

from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Authentication"]


class Authentication(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/auth")
        self.jwt_secret = bot.config.jwt_secret

    def setup(self):
        pass

    @commands.command(name="jwt", aliases=["dauth", "mcauth"])
    @commands.guild_only()
    async def jwt(self, ctx):
        """Generates a Javascript Web Token for a user"""

        time_since_join = ctx.author.joined_at - datetime.utcfromtimestamp(0)

        token = jwt.encode(
            {
                "iss": f"futaba-{ctx.guild.id}",
                "did": ctx.author.id,
                "dnn": ctx.author.display_name,
                "jdt": int(time_since_join.total_seconds() * 1000),
                "iat": int(datetime.now().timestamp()),
            },
            self.jwt_secret,
            algorithm="HS256",
        )

        logger.info("User '%s' (%d) generated a JWT", ctx.author.name, ctx.author.id)

        response = f"Generated authentication token:\n```{token}```"

        try:
            await ctx.author.send(content=response)
        except discord.Forbidden:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.title = "Cannot send help command"
            embed.description = (
                "You do not allow DMs from this server. "
                "Please enable them so help information can be sent."
            )

            await ctx.send(embed=embed)
