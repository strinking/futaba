#
# cogs/moderation/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Collection of moderation commands such as Ban/Kick
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import MemberConv, UserConv
from futaba.exceptions import CommandFailed, ManualCheckFailure
from futaba.utils import escape_backticks, plural, user_discrim

logger = logging.getLogger(__name__)

__all__ = [
    'Moderation',
]

class Moderation:
    '''
    Staff moderation commands
    '''

    __slots__ = (
        'bot',
        'journal',
        'mute_jobs',
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/moderation')
        self.mute_jobs = {}

    @commands.command(name='mute', aliases=['shitpost'])
    @commands.guild_only()
    @permissions.check_mod()
    async def mute(self, ctx, member: MemberConv, minutes: int, *, reason: str):
        '''
        Mutes the user for the given number of minutes.
        Requires a mute role to be configured.
        '''

        logger.info("Muting user '%s' (%d) for %d minutes", member.name, member.id, minutes)

        if minutes == 0:
            raise CommandFailed()

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.mute is None:
            raise CommandFailed(content='No configured mute role')

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permissions to mute this user")

        # TODO store punishment in table
        mod = user_discrim(ctx.author)
        full_reason = f'Muted by {mod} for {minutes} minute{plural(minutes)} with reason: {reason}'
        await member.add_roles(roles.mute, reason=full_reason)

        # TODO replace with navi
        async def remove_mute():
            await asyncio.sleep(minutes * 60)
            logger.info("Timed mute expired, removing role from '%s' (%d)", member.name, member.id)
            await member.remove_roles(roles.mute, reason='Mute expired')

        # Cancel old task, if any
        old_task = self.mute_jobs.get(member, None)
        if old_task is not None:
            old_task.cancel()

        # Add new task
        task = self.bot.loop.create_task(remove_mute())
        self.mute_jobs[member] = task

    @commands.command(name='unmute', aliases=['unshitpost'])
    @commands.guild_only()
    @permissions.check_mod()
    async def unmute(self, ctx, member: MemberConv, minutes: int = 0, *, reason: str = None):
        '''
        Unmutes the user, with an optional delay in minutes.
        Requires a mute role to be configured.
        '''

        logger.info("Unmuting user '%s' (%d) in %d minutes", member.name, member.id, minutes)

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.mute is None:
            raise CommandFailed(content='No configured mute role')

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permissions to unmute this user")

        # TODO store punishment in table
        mod = user_discrim(ctx.author)
        fmt_reason = f'with reason: {reason}' if reason else ''
        full_reason = f'Unmuted by {mod} {fmt_reason}'

        # TODO replace with navi
        async def remove_mute():
            await asyncio.sleep(minutes * 60)
            logger.info("Timed unmute expired, removing role from '%s' (%d)", member.name, member.id)
            await member.remove_roles(roles.mute, reason=full_reason)

        # Cancel old task, if any
        old_task = self.mute_jobs.get(member, None)
        if old_task is not None:
            old_task.cancel()

        # Add new task
        task = self.bot.loop.create_task(remove_mute())
        self.mute_jobs[member] = task

    @commands.command(name='jail', aliases=['dunce'])
    @commands.guild_only()
    @permissions.check_mod()
    async def jail(self, ctx, member: MemberConv, *, reason: str):
        '''
        Jails the user.
        Requires a jail role to be configured.
        '''

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.jail is None:
            raise CommandFailed(content='No configured jail role')

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permissions to jail this user")

        # TODO store punishment in table
        mod = user_discrim(ctx.author)
        await member.add_roles(roles.jail, reason=f'Jailed by {mod} with reason: {reason}')

    @commands.command(name='unjail', aliases=['undunce'])
    @commands.guild_only()
    @permissions.check_mod()
    async def unjail(self, ctx, member: MemberConv, *, reason: str = None):
        '''
        Removes a user from the jail.
        Requires a jail role to be configured.
        '''

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.jail is None:
            raise CommandFailed(content='No configured jail role')

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permissions to unjail this user")

        # TODO store punishment in table
        mod = user_discrim(ctx.author)
        fmt_reason = f'with reason: {reason}' if reason else ''
        await member.remove_roles(roles.jail, reason=f'Jail removed by {mod} {fmt_reason}')

    @commands.command(name='kick')
    @commands.guild_only()
    @permissions.check_mod()
    async def kick(self, ctx, member: MemberConv, *, reason: str):
        '''
        Kicks the user from the guild with a reason
        If guild has moderation logging enabled, it is logged
        '''

        try:
            embed = discord.Embed(description='Done! User Kicked')
            embed.add_field(name='Reason', value=reason)

            await ctx.guild.kick(member, reason=f'{reason} - {user_discrim(ctx.author)}')
            await ctx.send(embed=embed)

        except discord.errors.Forbidden:
            raise ManualCheckFailure(content="I don't have permissions to kick this user")

    @commands.command(name='ban')
    @commands.guild_only()
    @permissions.check_admin()
    async def ban(self, ctx, member: MemberConv, *, reason: str):
        '''
        Bans the user from the guild with a reason
        If guild has moderation logging enabled, it is logged
        '''

        try:
            embed = discord.Embed(description='Done! User Banned')
            embed.add_field(name='Reason', value=reason)

            mod = user_discrim(ctx.author)
            banned = user_discrim(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} banned {member.mention} ({banned}) with reason: `{clean_reason}`'

            await ctx.guild.ban(member, reason=f'{reason} - {mod}')
            await ctx.send(embed=embed)

            self.journal.send('member/ban', ctx.guild, content, icon='ban')

        except discord.errors.Forbidden:
            raise ManualCheckFailure(content="I don't have permissions to ban this user")

    @commands.command(name='softban', aliases=['soft', 'sban'])
    @commands.guild_only()
    @permissions.check_admin()
    async def softban(self, ctx, member: MemberConv, *, reason: str):
        '''
        Soft-bans the user from the guild with a reason.
        If guild has moderation logging enabled, it is logged

        Soft-ban is a kick that cleans up the chat
        '''

        try:
            embed = discord.Embed(description='Done! User Soft-banned')
            embed.add_field(name='Reason', value=reason)

            mod = user_discrim(ctx.author)
            banned = user_discrim(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} soft-banned {member.mention} ({banned}) with reason: `{clean_reason}`'

            # TODO add to tracker and add handler to journal event to prevent ban/softban event
            await ctx.guild.ban(member, reason=f'{reason} - {mod}', delete_message_days=1)
            await asyncio.sleep(0.1)
            await ctx.guild.unban(member, reason=f'{reason} - {mod}')
            await ctx.send(embed=embed)

            self.journal.send('member/softban', ctx.guild, content, icon='soft',
                    member=member, reason=reason, cause=ctx.author)

        except discord.errors.Forbidden:
            raise ManualCheckFailure(content="I don't have permissions to soft-ban this user")

    @commands.command(name='unban', aliases=['pardon'])
    @commands.guild_only()
    @permissions.check_admin()
    async def unban(self, ctx, member: UserConv, *, reason: str):
        '''
        Unbans the id from the guild with a reason.
        If guild has moderation logging enabled, it is logged
        '''

        try:
            embed = discord.Embed(description='Done! User Unbanned')
            embed.add_field(name='Reason', value=reason)

            # TODO add tracker unban event and move this to journal/impl/moderation.py
            mod = user_discrim(ctx.author)
            unbanned = user_discrim(member)
            clean_reason = escape_backticks(reason)
            content = f'{mod} unbanned {member.mention} ({unbanned}) with reason: `{clean_reason}`'

            await ctx.guild.unban(member, reason=f'{reason} - {mod}')
            await ctx.send(embed=embed)

            self.journal.send('member/unban', ctx.guild, content, icon='unban', member=member)

        except discord.errors.Forbidden:
            raise ManualCheckFailure(content="I don't have permissions to unban this user")
