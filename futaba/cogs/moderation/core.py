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
from futaba.utils import escape_backticks, user_disc

logger = logging.getLogger(__name__)

__all__ = [
    'Moderation',
]

BAN_ACTION = discord.AuditLogAction.ban
KICK_ACTION = discord.AuditLogAction.kick

class Moderation:
    '''
    Staff moderation commands
    '''

    __slots__ = (
        'bot',
        'journal',        
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/moderation')

    def __unload(self):
        ''' Remove listeners '''

        self.bot.remove_listener(self.member_ban, 'on_member_ban')
        self.bot.remove_listener(self.member_kick, 'on_member_remove')

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

            mod = user_disc(ctx.author)
            kicked = user_disc(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} kicked {member.mention} ({kicked}) with reason: `{clean_reason}`'
            
            await asyncio.gather(
                ctx.guild.kick(member, reason=f'{reason} - {mod}'),
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message)
            )

            self.journal.send('member/kick', ctx.guild, content, icon='kick')
        
        except discord.errors.Forbidden:            
            await asyncio.gather(
                ctx.send("Can't do that user has higher role than me"),
                Reactions.DENY.add(ctx.message)
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

            mod = user_disc(ctx.author)
            banned = user_disc(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} banned {member.mention} ({banned}) with reason: `{clean_reason}`'
            
            await asyncio.gather(
                ctx.guild.ban(member, reason=f'{reason} - {mod}'),
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message)
            )

            self.journal.send('member/ban', ctx.guild, content, icon='ban')
        
        except discord.errors.Forbidden:            
            await asyncio.gather(
                ctx.send("Can't do that user has higher role than me"),
                Reactions.DENY.add(ctx.message)
            )

    @commands.command(name='softban', aliases=['soft', 'sban',])
    @commands.guild_only()
    @permissions.check_admin()
    async def softban(self, ctx, member: discord.Member, *, reason: str):
        '''
        Soft-bans the user from the guild with a reason.
        If guild has moderation logging enabled, it is logged

        Soft-ban is a kick that cleans up the chat
        '''

        try:
            embed = discord.Embed(description='Done! User Soft-banned')
            embed.add_field(name='Reason:', value=reason)

            mod = user_disc(ctx.author)
            banned = user_disc(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} soft-banned {member.mention} ({banned}) with reason: `{clean_reason}`'
            
            await asyncio.gather(
                ctx.guild.ban(member, reason=f'{reason} - {mod}', delete_message_days=1),
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message)
            )

            await ctx.guild.unban(member, reason=f'{reason} - {mod}')

            self.journal.send('member/softban', ctx.guild, content, icon='soft')        
        
        except discord.errors.Forbidden:            
            await asyncio.gather(
                ctx.send("Can't do that user has higher role than me"),
                Reactions.DENY.add(ctx.message)
            )
    
    @commands.command()
    @commands.guild_only()
    @permissions.check_admin()
    async def unban(self, ctx, user_id: int, *, reason: str):
        '''
        Unbans the id from the guild with a reason.
        If guild has moderation logging enabled, it is logged
        '''

        try:
            member = self.bot.get_user(user_id)

            embed = discord.Embed(description='Done! User Unbanned')
            embed.add_field(name='Reason:', value=reason)

            mod = user_disc(ctx.author)
            unbanned = user_disc(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} unbanned {member.mention} ({unbanned}) with reason: `{clean_reason}`'
            
            await asyncio.gather(
                ctx.guild.unban(member, reason=f'{reason} - {mod}'),
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message)
            )

            self.journal.send('member/unban', ctx.guild, content, icon='unban')
        
        except discord.errors.Forbidden:            
            await asyncio.gather(
                ctx.send("Can't do that user has higher role than me"),
                Reactions.DENY.add(ctx.message)
            )

    async def member_ban(self, guild, user):
        ''' Event that is run on a members ban '''

        def find_banned_user(event):
            ''' Find the event for the banned user '''
            return event.target == user and event.user != guild.me

        # Check the audit log to get who banned the user
        ban_event = await guild.audit_logs(limit=1, action=BAN_ACTION).find(find_banned_user)

        if ban_event:
            mod = user_disc(ban_event.user)
            banned = user_disc(ban_event.target)
            clean_reason = escape_backticks(ban_event.reason)
            content = f'{mod} banned {ban_event.target.mention} ({banned}) with reason: `{clean_reason}`'

            self.journal.send('member/ban', guild, content, icon='ban')

    async def member_kick(self, member):
        '''
        Event that is run when a member leaves
        Used to check if someone was kicked
        '''

        guild = member.guild

        def find_kicked_user(event):
            ''' Find the event for the kicked user '''
            return event.target == member and event.user != guild.me

        # Check the audit log to get who kicked the user
        kick_event = await guild.audit_logs(limit=1, action=KICK_ACTION).find(find_kicked_user)

        if kick_event:
            mod = user_disc(kick_event.user)
            kicked = user_disc(kick_event.target)
            clean_reason = escape_backticks(kick_event.reason)
            content = f'{mod} kicked {kick_event.target.mention} ({kicked}) with reason: `{clean_reason}`'

            self.journal.send('member/kick', guild, content, icon='kick')