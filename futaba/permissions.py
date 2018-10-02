#
# permissions.py
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
Holds custom decorators to check permissions for commands.
Also has other helper commands for checking permissions within a guild.
'''

import discord
from discord.ext import commands

from futaba.str_builder import StringBuilder

__all__ = [
    'elevated_role_perms',
    'elevated_role_embed',
    'owner_perm',
    'admin_perm',
    'mod_perm',
    'check_owner',
    'check_admin',
    'check_mod',
]

ELEVATED_PERMISSION_NAMES = (
    'administrator',
    'mention_everyone',
    'manage_messages',
    'manage_channels',
    'manage_guild',
    'mute_members',
    'deafen_members',
    'move_members',
    'kick_members',
    'ban_members',
    'manage_nicknames',
    'manage_roles',
    'manage_emojis',
)

def elevated_role_perms(guild, role):
    '''
    Outputs a list of permissions and channels where this role has elevated permissions.
    If an empty list is returned it is "safe" to apply.
    '''

    # Format [(guild or channel, perm_name)...]
    elevated = []

    perms = role.permissions
    for perm in ELEVATED_PERMISSION_NAMES:
        if getattr(perms, perm) is True:
            elevated.append((guild, perm))
            if perm == 'administrator':
                break

    for channel in guild.channels:
        perms = channel.overwrites_for(role)
        for perm in ELEVATED_PERMISSION_NAMES:
            if getattr(perms, perm) is True:
                elevated.append((channel, perm))
                if perm == 'administrator':
                    break

    return elevated

def elevated_role_embed(guild, role, level):
    '''
    Takes the result of elevated_role_perms() and produces an embed listing the permissions.
    The parameter level must be 'warning' or 'error'.
    '''

    elevated = elevated_role_perms(guild, role)
    if not elevated:
        return None

    if level == 'warning':
        colour = discord.Colour.gold()
        icon = '\N{WARNING SIGN}'
    elif level == 'error':
        colour = discord.Colour.red()
        icon = '\N{NO ENTRY}'
    else:
        raise ValueError(f"Unknown severity level: '{level}'")

    embed = discord.Embed()
    embed.colour = colour
    embed.title = f'{icon} Role gives elevated permissions'
    descr = StringBuilder()
    for location, perm in elevated:
        perm = perm.replace('_', ' ').title()
        if isinstance(location, discord.Guild):
            descr.writeln(f'- {perm}')
        elif isinstance(location, discord.TextChannel):
            descr.writeln(f'- {perm} in {location.mention}')
        else:
            descr.writeln(f'- {perm} in {location.name}')
    embed.description = str(descr)
    return embed

def owner_perm(ctx: commands.Context):
    ''' Check if user is a owner of the bot from config '''

    return ctx.author.id in ctx.bot.config.owner_ids

def admin_perm(ctx: commands.Context):
    ''' Used to check is user has the manage_guild permission '''

    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False

    return ctx.channel.permissions_for(ctx.author).manage_guild

def mod_perm(ctx: commands.Context):
    ''' Used to check is user has the manage_channels permission '''

    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False

    return ctx.channel.permissions_for(ctx.author).manage_channels

def check_owner():
    ''' Check if user is a owner '''

    return commands.check(owner_perm)

def check_admin():
    ''' Check if user is admin or higher '''

    def checkperm(ctx):
        ''' Check the different perms '''
        return owner_perm(ctx) or admin_perm(ctx)

    return commands.check(checkperm)

def check_mod():
    ''' Check if user is moderator or higher '''

    def checkperm(ctx):
        ''' Check the different perms '''
        return owner_perm(ctx) or admin_perm(ctx) or mod_perm(ctx)

    return commands.check(checkperm)
