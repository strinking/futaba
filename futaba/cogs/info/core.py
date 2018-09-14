#
# cogs/info/core.py
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
Informational commands that make finding and gathering data easier.
'''

import asyncio
import logging
from itertools import islice

import discord
from discord.ext import commands

from futaba.enums import Reactions
from futaba.parse import get_user_id, similar_user_ids
from futaba.utils import fancy_timedelta

logger = logging.getLogger(__package__)

__all__ = [
    'Info',
]

class Info:
    '''
    Cog for informational commands.
    '''

    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='uinfo', aliases=['userinfo'])
    async def uinfo(self, ctx, *, name: str = None):
        '''
        Fetch information about a user, whether they are in the guild or not.
        If no argument is passed, the caller is checked instead.
        '''

        if name is None:
            name = str(ctx.message.author.id)

        logger.info("Running uinfo on '%s'", name)

        id = get_user_id(name, self.bot.users)
        if id is None:
            logger.debug("No user ID found!")
            await Reactions.FAIL.add(ctx.message)
            return

        logger.debug("Fetched user ID is %d", id)

        user = None
        if ctx.guild is not None:
            user = ctx.guild.get_member(id)

        if user is None:
            user = self.bot.get_user(id)
            if user is None:
                user = await self.bot.get_user_info(id)
                if user is None:
                    logger.debug("No user with that ID found!")
                    await Reactions.FAIL.add(ctx.message)
                    return

        logger.debug("Found user! %r", user)

        # Status
        if getattr(user, 'status', None):
            status = 'do not disturb' if user.status == discord.Status.dnd else user.status
            descr = f'{user.mention}, {status}'
        else:
            descr = user.mention

        embed = discord.Embed(description=descr)
        embed.timestamp = user.created_at
        embed.set_author(name=f'{user.name}#{user.discriminator}')
        embed.set_thumbnail(url=user.avatar_url)

        # User colour
        if hasattr(user, 'colour'):
            embed.colour = user.colour

        # User id
        embed.add_field(name='ID:', value=f'`{user.id}`')

        # Roles
        if getattr(user, 'roles', None):
            roles = ' '.join(role.mention for role in islice(user.roles, 1, len(user.roles)))
            if roles:
                embed.add_field(name='Roles:', value=roles)

        # Current game
        if getattr(user, 'activity', None):
            act = user.activity
            if isinstance(act, discord.Game):
                if act.start is None:
                    if act.end is None:
                        time_msg = ''
                    else:
                        time_msg = f'until {act.end}'
                else:
                    if act.end is None:
                        time_msg = f'since {act.start}'
                    else:
                        time_msg = f'from {act.start} to {act.end}'

                embed.description += f'\nPlaying `{act.name}` {time_msg}'
            elif isinstance(act, discord.Streaming):
                embed.description += f'\nStreaming [{act.name}]({act.url})'
                if act.details is not None:
                    embed.description += f'\n{act.details}'
            elif isinstance(act, discord.Activity):
                embed.description += '\n{act.state} [{act.name}]({act.url})'

        # Voice activity
        if getattr(user, 'voice', None):
            mute = user.voice.mute or user.voice.self_mute
            deaf = user.voice.deaf or user.voice.self_deaf

            states = []
            if mute:
                states.append('muted')
            if deaf:
                states.append('deafened')

            if states:
                state = ', '.join(states)
            else:
                state = 'active'

            embed.add_field(name='Voice:', value=state)

        # Guild join date
        if hasattr(user, 'joined_at'):
            embed.add_field(name='Member for:', value=fancy_timedelta(user.joined_at))

        # Discord join date
        embed.add_field(name='Account age:', value=fancy_timedelta(user.created_at))

        # Send them
        await asyncio.gather(
            Reactions.SUCCESS.add(ctx.message),
            ctx.send(embed=embed),
        )

    @commands.command(name='ufind', aliases=['userfind', 'usearch', 'usersearch'])
    async def ufind(self, ctx, *, name: str):
        '''
        Perform a fuzzy search to find users who match the given name.
        They are listed with the closest matches first.
        '''

        logger.info("Running ufind on '%s'", name)
        user_ids = similar_user_ids(name, self.bot.users)
        users_in_guild = set(member.id for member in getattr(ctx.guild, 'members', []))

        lines = ['**Users found:**']
        for user_id in user_ids:
            user = self.bot.get_user(user_id)
            if user is None:
                user = await self.bot.get_user_info(user_id)

            logger.debug("Result for user ID %d: %r", user_id, user)
            if user is not None:
                extra = '' if user_id in users_in_guild else '\N{GLOBE WITH MERIDIANS}'
                lines.append(f'- {user.mention} {extra}')

        if len(lines) > 1:
            descr = '\n'.join(lines)
            colour = discord.Colour.teal()
        else:
            descr = '**No users found!**'
            colour = discord.Colour.dark_red()

        embed = discord.Embed(description=descr, colour=colour)
        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='ginfo', aliases=['guildinfo'])
    @commands.guild_only()
    async def ginfo(self, ctx):
        ''' Gets information about the current guild. '''

        embed = discord.Embed()
        embed.timestamp = ctx.guild.created_at
        embed.set_author(name=ctx.guild.name)
        embed.set_thumbnail(url=ctx.guild.icon_url)

        lines = [
            f'\N{MAN} **Members:** {len(ctx.guild.members)}',
            f'\N{MILITARY MEDAL} **Roles:** {len(ctx.guild.roles)}',
            f'\N{BAR CHART} **Channel categories:** {len(ctx.guild.categories)}',
            f'\N{MEMO} **Text Channels:** {len(ctx.guild.text_channels)}',
            f'\N{STUDIO MICROPHONE} **Voice Channels:** {len(ctx.guild.voice_channels)}',
            f'\N{CLOCK FACE TWO OCLOCK} **Age:** {fancy_timedelta(ctx.guild.created_at)}',
            ''
        ]

        moderators = 0
        admins = 0
        bots = 0

        # Do a single loop instead of generator expressions
        for member in ctx.guild.members:
            if member.bot:
                bots += 1

            perms = member.permissions_in(ctx.channel)
            if perms.administrator:
                admins += 1
            elif perms.manage_messages:
                moderators += 1

        if bots:
            lines.append(f'\N{ROBOT FACE} **Bots:** {bots}')
        if moderators:
            lines.append(f'\N{CONSTRUCTION WORKER} **Moderators:** {moderators}')
        if admins:
            lines.append(f'\N{POLICE OFFICER} **Administrators:** {admins}')
        lines.append(f'\N{CROWN} **Owner:** {ctx.guild.owner.mention}')

        embed.description = '\n'.join(lines)

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )
