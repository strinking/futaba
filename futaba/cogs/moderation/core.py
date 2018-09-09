#
# cogs/moderation/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

# pylint: skip-file

'''
Collection of moderation commands such as Ban/Kick
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions

logger = logging.getLogger(__package__)

class Moderation:
    '''
    Staff moderation commands
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.guild_only()
    @permissions.check_mod()
    async def kick(self, ctx, member: discord.Member, *, reason: str):
        '''
        Kicks the user from the guild with a reason
        If guild has moderation logging enabled, it is logged
        '''

        try:
            embed = discord.Embed(description='Done! User Kicked')
            embed.add_field(name='Reason:', value=reason)
            
            await asyncio.gather(
                ctx.guild.kick(member, reason=reason),
                Reactions.SUCCESS.add(ctx.message),
                ctx.send(embed=embed)
            )

            #TODO Send log about the kick using built-in util 
        
        except discord.errors.Forbidden:
            
            await asyncio.gather(
                Reactions.DENY.add(ctx.message),
                ctx.send("Can't do that user has higher role than me")
            )
    
    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def ban(self, ctx, member: discord.Member, *, reason: str):
        '''
        Bans the user from the guild with a reason
        If guild has moderation logging enabled, it is logged
        '''

        try:
            embed = discord.Embed(description='Done! User Banned')
            embed.add_field(name='Reason:', value=reason)
            
            await asyncio.gather(
                ctx.guild.ban(member, reason=reason),
                Reactions.SUCCESS.add(ctx.message),
                ctx.send(embed=embed)
            )

            #TODO Send log about the kick using built-in util 
        
        except discord.errors.Forbidden:
            
            await asyncio.gather(
                Reactions.DENY.add(ctx.message),
                ctx.send("Can't do that user has higher role than me")
            )

