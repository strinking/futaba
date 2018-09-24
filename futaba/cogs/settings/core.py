#
# cogs/settings/core.py
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
Cog for all commands that change bot settings. It ensures persistence
of configured settings in between runs of the bot.
'''

import asyncio
import logging

import discord
from discord.ext import commands

from futaba import permissions
from futaba.emojis import ICONS
from futaba.enums import Reactions
from futaba.parse import get_role_id
from futaba.utils import escape_backticks

logger = logging.getLogger(__name__)

__all__ = [
    'Settings',
]

class Settings:
    __slots__ = (
        'bot',
    )

    def __init__(self, bot):
        self.bot = bot

        for guild in bot.guilds:
            bot.sql.settings.get_special_roles(guild)

    @commands.command(name='specroles', aliases=['sroles'])
    @commands.guild_only()
    async def special_roles(self, ctx):
        ''' Retrieves all configured roles for this guild. '''

        logger.info("Sending list of all configured roles for guild '%s' (%d)",
                ctx.guild.name, ctx.guild.id)

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        mention = lambda role: getattr(role, 'mention', '(none)')

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = '\n'.join((
            f'{ICONS["member"]} Member: {mention(roles.member)}',
            f'{ICONS["guest"]} Guest: {mention(roles.guest)}',
            f'{ICONS["mute"]} Mute: {mention(roles.mute)}',
            f'{ICONS["jail"]} Jail: {mention(roles.jail)}',
        ))

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    async def get_role(self, ctx, name, check_roles=True):
        role_id = get_role_id(name, ctx.guild.roles)
        role = discord.utils.get(ctx.guild.roles, id=role_id)
        embed = discord.Embed(colour=discord.Colour.dark_red())
        if role is None:
            embed.description = 'No role with description `{escape_backticks(name)}` found'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            return None
        elif role.is_default():
            embed.description = '@everyone role cannot be assigned for this purpose'
            await asyncio.gather(
                ctx.send(embed=embed),
                Reactions.FAIL.add(ctx.message),
            )
            return None
        elif check_roles:
            special_roles = self.bot.sql.settings.get_special_roles(ctx.guild)
            if role in special_roles:
                embed.description = f'Cannot assign the same role for multiple purposes'
                await asyncio.gather(
                    ctx.send(embed=embed),
                    Reactions.FAIL.add(ctx.message),
                )
                return None
        else:
            return role

    @commands.command(name='setmember')
    @commands.guild_only()
    @permissions.check_mod()
    async def set_member_role(self, ctx, *, name: str = None):
        ''' Set the member role for this guild. No argument to unset. '''

        logger.info("Setting member role for guild '%s' (%d) to '%s",
                ctx.guild.name, ctx.guild.id, name)

        if name is None:
            role = None
        else:
            role = await self.get_role(ctx, name)
            if role is None:
                return

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, member=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f'Set member role to {role.mention}'
        else:
            embed.description = 'Unset member role'

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='setguest')
    @commands.guild_only()
    @permissions.check_mod()
    async def set_guest_role(self, ctx, *, name: str):
        ''' Set the guest role for this guild. '''

        logger.info("Setting guest role for guild '%s' (%d) to '%s",
                ctx.guild.name, ctx.guild.id, name)

        if name is None:
            role = None
        else:
            role = await self.get_role(ctx, name)
            if role is None:
                return

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, guest=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f'Set guest role to {role.mention}'
        else:
            embed.description = 'Unset guest role'

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='setmute')
    @commands.guild_only()
    @permissions.check_mod()
    async def set_mute_role(self, ctx, *, name: str):
        ''' Set the mute role for this guild. '''

        logger.info("Setting mute role for guild '%s' (%d) to '%s",
                ctx.guild.name, ctx.guild.id, name)

        if name is None:
            role = None
        else:
            role = await self.get_role(ctx, name)
            if role is None:
                return

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, mute=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f'Set mute role to {role.mention}'
        else:
            embed.description = 'Unset mute role'

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )

    @commands.command(name='setjail')
    @commands.guild_only()
    @permissions.check_mod()
    async def set_jail_role(self, ctx, *, name: str):
        ''' Set the mute role for this guild. '''

        logger.info("Setting mute role for guild '%s' (%d) to '%s",
                ctx.guild.name, ctx.guild.id, name)

        if name is None:
            role = None
        else:
            role = await self.get_role(ctx, name)
            if role is None:
                return

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, jail=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f'Set jail role to {role.mention}'
        else:
            embed.description = 'Unset jail role'

        await asyncio.gather(
            ctx.send(embed=embed),
            Reactions.SUCCESS.add(ctx.message),
        )
