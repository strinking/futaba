#
# cogs/info/alias.py
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
Tracking for aliases of members, storing previous usernames, nicknames, and avatars.
'''

import asyncio
import logging
import re
from datetime import datetime

import discord
from discord.ext import commands

from futaba.download import download_link
from futaba.enums import Reactions
from futaba.parse import get_user_id
from futaba.str_builder import StringBuilder
from futaba.utils import fancy_timedelta

logger = logging.getLogger(__package__)

__all__ = [
    'Alias',
]

EXTENSION_REGEX = re.compile(r'\.([a-z]+)')

class MemberChanges:
    __slots__ = (
        'avatar_url',
        'username',
        'nickname',
    )

    def __init__(self):
        self.avatar_url = None
        self.username = None
        self.nickname = None

    def __bool__(self):
        for field in self.__slots__:
            if getattr(self, field) is not None:
                return True
        return False

class Alias:
    '''
    Cog for member alias information.
    '''

    __slots__ = (
        'bot',
    )

    def __init__(self, bot):
        self.bot = bot

    async def member_update(self, before, after):
        ''' Handles update of member information. '''

        changes = MemberChanges()
        timestamp = datetime.now()

        if before.avatar != after.avatar:
            logger.info("Member '%s' (%d) has changed their profile picture (%s)",
                    before.name, before.id, after.avatar)
            changes.avatar_url = after.avatar_url

        if before.name != after.name:
            logger.info("Member '%s' (%d) has changed name to '%s'",
                    before.name, before.id, after.name)
            changes.username = after.name

        if before.nick != after.nick and after.nick is not None:
            logger.info("Member '%s' (%d) has changed nick to '%s'",
                    before.display_name, before.id, after.nick)
            changes.nickname = after.nick

        # Check if there were any changes
        if not changes:
            return

        if changes.avatar_url is not None:
            avatar = await download_link(changes.avatar_url)
            avatar_ext = EXTENSION_REGEX.match(changes.avatar_url)[1]

        with self.bot.sql.transaction():
            if changes.avatar_url is not None:
                self.bot.sql.alias.add_avatar(before, timestamp, avatar, avatar_ext)
            if changes.username is not None:
                self.bot.sql.alias.add_username(before, timestamp, changes.username)
            if changes.nickname is not None:
                self.bot.sql.alias.add_nickname(before, timestamp, changes.nickname)

    @commands.command(name='aliases')
    async def aliases(self, ctx, name: str):
        ''' Gets information about known aliases of the given user. '''

        logger.info("Getting and printing alias information for some user '%s'", name)

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name='Member alias information')

        user = await self.bot.find_user(name, ctx.guild)
        if user is None:
            embed.colour = discord.Colour.dark_red()
            embed.description = f'No user information found for `{name}`'

            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            return

        logger.debug("Found user! %r. Now fetching alias information...", user)
        avatars, usernames, nicknames = self.bot.sql.alias.get_aliases(user)

        if not any((avatars, usernames, nicknames)):
            embed.colour = discord.Colour.dark_purple()
            embed.description = f'No information found for {user.mention}'

            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.SUCCESS.add(ctx.message),
            )
            return

        embed.description = f'**Alias information for {user.mention}:**\n'
        content = StringBuilder()
        files = []

        if avatars:
            for i, (avatar_bin, avatar_ext, timestamp) in enumerate(avatars, 1):
                time_since = fancy_timedelta(timestamp)
                content.writeln(f'#{i} set {time_since} ago')
                files.append(discord.File(avatar_bin, filename=f'avatar {time_since}.{avatar_ext}'))
            embed.add_field(name='Past avatars', value=str(content))
            content.clear()

        if usernames:
            for username, timestamp in usernames:
                content.writeln(f'- `{username}` set {fancy_timedelta(timestamp)} ago')
            embed.add_field(name='Past usernames', value=str(content))
            content.clear()

        if nicknames:
            for nickname, timestamp in nicknames:
                content.writeln(f'- `{nickname}` set {fancy_timedelta(timestamp)} ago')
            embed.add_field(name='Past nicknames', value=str(content))
            content.clear()

        await asyncio.gather(
            ctx.send(embed=embed, files=files),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='altadd')
    @commands.guild_only()
    async def add_alt(self, ctx, first_name: str, second_name: str):
        ''' Add a suspected alternate account for a user. '''

        logger.info("Adding suspected alternate account pair for '%s' and '%s'", first_name, second_name)
        first_user, second_user = await asyncio.gather(
            self.bot.find_user(first_name, ctx.guild),
            self.bot.find_user(second_name, ctx.guild),
        )

        embed = discord.Embed(colour=discord.Colour.dark_red())
        content = StringBuilder()

        if first_user is None:
            content.writeln(f'No user information found for `{first_name}`')
        if second_user is None:
            content.writeln(f'No user information found for `{second_name}`')
        if content:
            embed.description = str(content)
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            return

        with self.bot.sql.transaction():
            self.bot.sql.add_alias(ctx.guild, first_user, second_user)

        await Reactions.SUCCESS.add(ctx.message)
