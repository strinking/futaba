#
# converters/role.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging
import re

import discord
from discord.ext.commands import BadArgument, Converter

from futaba.unicode import normalize_caseless

from .utils import ID_REGEX

logger = logging.getLogger(__name__)

__all__ = [
    'RoleConv',
]

ROLE_MENTION_REGEX = re.compile(r'<@&([0-9]+)>')

class RoleConv(Converter):
    async def convert(self, ctx, argument) -> discord.Role:
        if ctx.guild is None:
            raise BadArgument(f'Unable to find role because we are not in a guild')

        logger.debug("Checking if it's a role ID")
        match = ID_REGEX.match(argument)
        if match is not None:
            role = ctx.guild.get_role(int(match[1]))
            if role is not None:
                return role

        logger.debug("Checking if it's a role mention")
        match = ROLE_MENTION_REGEX.match(argument)
        if match is not None:
            role = ctx.guild.get_role(int(match[1]))
            if role is not None:
                return role

        logger.debug("Checking if it's a role's name")
        role = discord.utils.get(ctx.guild.roles, name=argument)
        if role is not None:
            return role

        logger.debug("Checking if it's a role's name (case-insensitive)")
        argument = normalize_caseless(argument)
        role = discord.utils.find(lambda r: argument == normalize_caseless(r.name), ctx.guild.roles)
        if role is not None:
            return role

        logger.debug("Checking if it's the default role")
        if argument in ('@everyone', 'everyone', '@here', 'here', 'default'):
            return ctx.guild.default_role

        return BadArgument(f'Unable to find role with description "{argument}"')
