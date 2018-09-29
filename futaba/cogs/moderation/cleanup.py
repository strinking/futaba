#
# cogs/moderation/cleanup.py
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
Commands related to cleaning up messages in bulk.
'''

import asyncio
import json
import logging
from io import BytesIO

import discord
from discord.ext import commands

from futaba import permissions
from futaba.enums import Reactions
from futaba.utils import message_to_dict

logger = logging.getLogger(__name__)

__all__ = [
    'Cleanup',
]

class Cleanup:
    __slots__ = (
        'bot',
        'journal',
        'dump',
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/moderation/cleanup')
        self.dump = bot.get_max_delete_messages('/dump/moderation/cleanup')

    @commands.command(name='cleanup', aliases=['clean'])
    @commands.guild_only()
    @permissions.check_mod()
    async def cleanup(self, ctx, count: int, channel: discord.TextChannel = None):
        ''' Deletes the last <count> messages, not including this command. '''

        max_count = self.bot.sql.settings.get_max_delete_messages()
        if count < 1:
            await asyncio.gather(
                ctx.send(content=f'Invalid message count: {count}'),
                Reactions.FAIL.add(ctx.message),
            )
            return
        elif count > max_count:
            await asyncio.gather(
                ctx.send(content=f'Count too high. Maximum configured for this guild is {max_count}.'),
                Reactions.FAIL.add(ctx.message),
            )
            return

        if channel is None:
            channel = ctx.channel

        # Delete the messages
        messages = await channel.purge(limit=count, before=ctx.message, bulk=True)
        content = f'Deleted {count} messages from {channel.mention}'
        self.journal.send('count', ctx.guild, content, icon='delete',
                count=count, channel=channel, cause=ctx.author)

        # Dump deleted messages to JSON
        buffer = BytesIO()
        json.dump(list(map(message_to_dict, messages)), buffer)
        file = discord.File(buffer, filename='deleted-messages.json')
        self.dump.send('count', ctx.guild, content, icon='delete', file=file)
