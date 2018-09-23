#
# cogs/welcome/core.py
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
Cog for greeting new members, accepting !agree commands, and applying Member and Guest roles.
'''

import asyncio
import logging
from collections import deque, namedtuple

import discord
from discord.ext import commands

from futaba.exceptions import InvalidCommandContext
from futaba.utils import user_discrim

FakeContext = namedtuple('FakeContext', ('author', 'channel', 'guild'))
logger = logging.getLogger(__package__)

__all__ = [
    'format_welcome_message',
    'Welcome',
]

def format_welcome_message(welcome_message, ctx):
    user = ctx.author
    channel = ctx.channel
    guild = ctx.guild

    return welcome_message.format(
        mention=user.mention,
        user=user.name,
        discrim=user.discriminator,
        userdiscrim=user_discrim(user),
        user_id=user.id,
        channel=channel.mention,
        channel_name=channel.name,
        channel_id=channel.id,
        server=guild.name,
        server_id=guild.id,
        guild=guild.name,
        guild_id=guild.id,
    )

class Welcome:
    __slots__ = (
        'bot',
        'recently_joined',
    )

    def __init__(self, bot):
        self.bot = bot
        self.recently_joined = deque(maxlen=5)

    async def member_join(self, member):
        logger.info("Member %s (%d) joined '%s' (%d)",
                user_discrim(member), member.id, member.guild.name, member.guild.id)

        welcome = self.bot.sql.welcome.get_welcome(member.guild)
        roles = self.bot.sql.settings.get_special_roles(member.guild)

        if welcome.welcome_message and welcome.channel:
            ctx = FakeContext(author=member, channel=welcome.channel, guild=member.guild)
            content = format_welcome_message(welcome.welcome_message, ctx)
            await welcome.channel.send(content=content)

        if roles.guest:
            logger.info("Adding role %s (%d) to new guest", roles.guest.name, roles.guest.id)
            await member.add_roles(roles.guest, reason="New user joined")

    async def member_leave(self, member):
        logger.info("Member %s (%d) left '%s' (%d)",
                user_discrim(member), member.id, member.guild.name, member.guild.id)

        welcome = self.bot.sql.welcome.get_welcome(member.guild)

        if welcome.goodbye_message and welcome.channel:
            ctx = FakeContext(author=member, channel=welcome.channel, guild=member.guild)
            content = format_welcome_message(welcome.goodbye_message, ctx)
            await welcome.channel.send(content=content)

    @commands.command(name='agree', aliases=['accept'])
    @commands.guild_only()
    async def agree(self, ctx):
        '''
        Designate that you have agreed to the rules and other server information.
        Required to be able to access the server.
        '''

        logger.debug("Unchecked !agree command received")

        welcome = self.bot.sql.get_welcome(ctx.guild)
        roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        if ctx.channel != welcome.channel:
            # Not the welcome channel, ignore
            raise InvalidCommandContext()

        if ctx.author.permissions_in(ctx.channel).manage_messages:
            # Not a guest, ignore
            raise InvalidCommandContext()

        if ctx.author in self.recently_joined:
            # Already joining, ignore
            raise InvalidCommandContext()

        logger.info("Guest %s (%d) just agreed to the rules and policies!",
                ctx.author.name, ctx.author.id)

        self.recently_joined.append(ctx.author)

        if roles.member:
            logger.info("Adding member role %s (%d)", roles.member.name, roles.member.id)
            await ctx.author.add_roles(roles.member, reason='Agreed to the rules and policies')

        if roles.guest:
            logger.info("Removing guest role %s (%d)", roles.guest.name, roles.guest.id)
            await ctx.author.remove_roles(roles.guest, reason='Agreed to the rules and policies')

        if welcome.agreed_message:
            await ctx.send(content=format_welcome_message(welcome.agreed_message, ctx))

        # TODO: restore old roles

        if welcome.delete_on_agree:
            await ctx.message.delete()

            # Prevent the bot from attempting to add a success reaction
            raise InvalidCommandContext()
