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

from futaba import permissions
from futaba.enums import Reactions
from futaba.exceptions import InvalidCommandContext, SendHelp
from futaba.utils import user_discrim

FakeContext = namedtuple('FakeContext', ('author', 'channel', 'guild'))
logger = logging.getLogger(__package__)

__all__ = [
    'format_welcome_message',
    'Welcome',
]

AGREE_REASON = "User agreed to the server's rules and policies"

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
        'journal',
        'recently_joined',
    )

    def __init__(self, bot):
        self.bot = bot
        self.journal = bot.get_broadcaster('/welcome')
        self.recently_joined = deque(maxlen=5)

    @staticmethod
    async def send_welcome_message(member, format_message, channel):
        ctx = FakeContext(author=member, channel=channel, guild=member.guild)
        content = format_welcome_message(format_message, ctx)
        await channel.send(content=content)

    async def member_join(self, member):
        logger.info("Member %s (%d) joined '%s' (%d)",
                user_discrim(member), member.id, member.guild.name, member.guild.id)

        welcome = self.bot.sql.welcome.get_welcome(member.guild)
        roles = self.bot.sql.settings.get_special_roles(member.guild)
        tasks = []

        if welcome.welcome_message and welcome.channel:
            tasks.append(self.send_welcome_message(member, welcome.welcome_message, welcome.channel))

        if roles.guest:
            logger.info("Adding role %s (%d) to new guest", roles.guest.name, roles.guest.id)
            tasks.append(member.add_roles(roles.guest, reason="New user joined"))

        await asyncio.gather(*tasks)

    async def member_leave(self, member):
        logger.info("Member %s (%d) left '%s' (%d)",
                user_discrim(member), member.id, member.guild.name, member.guild.id)

        welcome = self.bot.sql.welcome.get_welcome(member.guild)

        if welcome.goodbye_message and welcome.channel:
            await self.send_welcome_message(member, welcome.goodbye_message, welcome.channel)

    @commands.command(name='agree', aliases=['accept'], hidden=True)
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
        tasks = []

        if welcome.delete_on_agree:
            tasks.append(ctx.message.delete())

        if roles.member:
            logger.info("Adding member role %s (%d)", roles.member.name, roles.member.id)
            tasks.append(ctx.author.add_roles(roles.member, reason=AGREE_REASON))

        if roles.guest:
            logger.info("Removing guest role %s (%d)", roles.guest.name, roles.guest.id)
            tasks.append(ctx.author.remove_roles(roles.guest, reason=AGREE_REASON))

        if welcome.agreed_message:
            tasks.append(ctx.send(content=format_welcome_message(welcome.agreed_message, ctx)))

        # TODO: restore old roles

        # Run all tasks in parallel
        await asyncio.gather(*tasks)

        # Prevent the bot from attempting to add a success reaction
        if welcome.delete_on_agree:
            raise InvalidCommandContext()

    @commands.group(name='welcome', aliases=['wlm'])
    @commands.guild_only()
    async def welcome(self, ctx):
        ''' Manages the welcome cog for managing new users and roles. '''

        print('>>', ctx.command, ctx.invoked_with, ctx.kwargs)
        print('$$', ctx.invoked_subcommand)
        if ctx.invoked_subcommand is None:
            raise SendHelp(ctx.command)

    @welcome.command(name='getchan')
    @commands.guild_only()
    async def get_welcome_channel(self, ctx):
        ''' Gets the welcome channel. '''

        welcome = self.bot.sql.welcome.get_welcome(ctx.guild)
        if welcome.channel:
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = f'Welcome channel set to {welcome.channel.mention}'
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = 'No welcome channel set for this guild!'

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @welcome.command(name='setchan')
    @commands.guild_only()
    @permissions.check_admin()
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        ''' Sets the welcome channel. '''

        logger.info("Setting welcome channel to #%s (%d) in guild '%s' (%d)",
                channel.name, channel.id, ctx.guild.name, ctx.guild.id)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_welcome_channel(ctx.guild, channel)

        content = f'{user_discrim(ctx.author)} set the welcome channel to {channel.mention}'
        self.journal.send('channel/set', ctx.guild, content, icon='settings',
                channel=channel, cause=ctx.author)

    @welcome.command(name='unsetchan')
    @commands.guild_only()
    @permissions.check_admin()
    async def unset_welcome_channel(self, ctx):
        ''' Unsets the welcome channel. '''

        logger.info("Unsetting the welcome channel in guild '%s' (%d)",
                ctx.guild.name, ctx.guild.id)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_welcome_channel(ctx.guild, None)

        content = f'{user_discrim(ctx.author)} unset the welcome channel'
        self.journal.send('channel/set', ctx.guild, content, icon='settings',
                channel=None, cause=ctx.author)
