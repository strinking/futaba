#
# cogs/info/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017 Jake Richardson, Ammon Smith, jackylam5
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
import re
from datetime import datetime

import discord
from discord.ext import commands

from futaba.enums import Reactions
from futaba.parse import get_user_id
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
    async def uinfo(self, ctx, name: str = None):
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
                logger.debug("No user with that ID found!")
                await Reactions.FAIL.add(ctx.message)
                return

        logger.debug("Found user! %r", user)

        embed = discord.Embed(description=user.mention)
        embed.timestamp = user.created_at
        embed.set_author(name=f'{user.name}#{user.discriminator}')
        embed.set_thumbnail(url=user.avatar_url)

        # User colour
        if hasattr(user, 'colour'):
            embed.colour = user.colour

        embed.add_field(name='ID:', value=f'`{user.id}`')

        # Roles
        if getattr(user, 'roles', None):
            roles = ' '.join(role.mention for role in user.roles[1:])
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

        # Join date
        if hasattr(user, 'joined_at'):
            embed.add_field(name='Member for:', value=fancy_timedelta(user.joined_at))

        # Send them
        await asyncio.gather(
            Reactions.SUCCESS.add(ctx.message),
            ctx.send(embed=embed),
        )
