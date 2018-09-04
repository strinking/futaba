#
# permissions.py
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
Holds custom decorators to check permissions for commands
'''

import discord
from discord.ext import commands

__all__ = [
    'check_owner',
    'check_admin',
    'check_mod',
]

def check_owner_perm(ctx: commands.Context):
    '''
    Check if user is a owner of the bot from config
    '''

    return ctx.author.id in ctx.bot.config.owner_ids

def check_admin_perm(ctx: commands.Context):
    '''
    Used to check is user has the manage_guild permission
    '''

    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False

    return ctx.channel.permissions_for(ctx.author).manage_guild

def check_mod_perm(ctx: commands.Context):
    '''
    Used to check is user has the manage_channels permission
    '''

    if isinstance(ctx.channel, discord.abc.PrivateChannel):
        return False

    return ctx.channel.permissions_for(ctx.author).manage_channels

def check_owner():
    '''
    Check if user is a owner
    '''

    return commands.check(check_owner_perm)

def check_admin():
    '''
    Check if user is admin or higher
    '''

    def checkperm(ctx):
        ''' Check the different perms '''
        return check_owner_perm(ctx) or check_admin_perm(ctx)

    return commands.check(checkperm)

def check_mod():
    '''
    Check if user is moderator or higher
    '''

    def checkperm(ctx):
        ''' Check the different perms '''
        return check_owner_perm(ctx) or check_admin_perm(ctx) or check_mod_perm(ctx)

    return commands.check(checkperm)
