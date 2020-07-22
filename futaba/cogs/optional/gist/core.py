#
# cogs/optional/example/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Cog for creating gists from messages
"""

# REMOVE THIS IN REGULAR COGS:
# pylint: disable=unused-import

import asyncio
import logging
import math

import discord
from discord.ext import commands

from futaba import permissions
from futaba.cogs.abc import AbstractCog
from futaba.converters import MessageConv
from futaba.exceptions import CommandFailed, ManualCheckFailure, SendHelp
from futaba.permissions import mod_perm

from .gist import create_single_gist

logger = logging.getLogger(__name__)


class Gist(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/gist")
        self.default_settings = {
            "token": "",
            "description": "Messages uploaded by futaba",
            "filename": "messages.md",
            "public": False,
        }

    def setup(self):
        # Fetching information from the database for this cog
        pass

    def get_settings(self, guild):
        return self.bot.sql.settings.get_optional_cog_settings(guild, "gist")

    def set_settings(self, guild, settings):
        return self.bot.sql.settings.set_optional_cog_settings(guild, "gist", settings)

    def change_setting(self, guild, setting, value):
        settings = self.get_settings(guild)

        if len(settings) == 0:
            settings = self.default_settings

        settings[setting] = value

        self.set_settings(guild, settings)

    @commands.command(name="gist", aliases=["msgupload"])
    @commands.guild_only()
    async def upload_message(self, ctx, *messages: MessageConv):
        """
        Concatenates the range of messages and upload to a gist.
        A link to the gist is posted after a successful upload.
        """
        if len(messages) == 0:
            raise CommandFailed(
                content="Please specify the messages that should be uploaded."
            )

        settings = self.get_settings(ctx.guild)
        oauth_token = settings.get("token")

        if not oauth_token:
            raise CommandFailed(content="The gist oauth token is not configured.")

        messages_content = "\n".join(str(message.content) for message in messages)
        messages_ids = ", ".join(str(message.id) for message in messages)

        # github markdown requires that 2 spaces are placed before a newline character
        messages_content = messages_content.replace("\n", "  \n")

        gist_url = await create_single_gist(
            token=oauth_token,
            content=messages_content,
            filename=settings.get("filename"),
            description=settings.get("description"),
            public=settings.get("public"),
        )

        logger.info(
            "Successfully uploaded %d messages[%s] into a gist. Requested by user '%s' (id=%d, guild=%d)",
            len(messages),
            messages_ids,
            ctx.author.name,
            ctx.author.id,
            ctx.guild.id,
        )

        embed = discord.Embed(description="Done! Messages successfully uploaded!")
        embed.add_field(name="Permalink", value=gist_url)
        embed.colour = discord.Colour.dark_teal()

        await ctx.send(embed=embed)

    @commands.command(name="mvgist", aliases=["msgcollapse"])
    @commands.guild_only()
    async def collapse_message(self, ctx, *messages: MessageConv):
        """
        Concatenates the range of messages and uploads to a gist.
        The original messages are deleted and a link to the gist is posted.

        Note: The messages specified should be by the same user
        """

        if not permissions.has_perm(ctx, "manage_messages") and any(
            message.author.id != ctx.author.id for message in messages
        ):
            # check if the messages were created by the same user
            raise ManualCheckFailure(content="I can only collapse your messages")

        await self.upload_message(ctx, *messages)

        for message in messages:
            await message.delete()

        logger.info(
            "Removed %d messages because of message collapse request by user '%s'(id=%d, guild=%d)",
            len(messages),
            ctx.author.name,
            ctx.author.id,
            ctx.guild.id,
        )

    @commands.group(name="gistconf")
    @commands.guild_only()
    async def gist_settings(self, ctx):
        """ Manages settings related to gists """

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @gist_settings.command(name="get")
    @commands.guild_only()
    @permissions.check_admin()
    async def settings_get(self, ctx, setting: str = None):
        """
        Gets the current settings
        Optionally a setting name can be specified
        """

        settings = self.get_settings(ctx.guild)

        embed = discord.Embed(
            description="Gist cog settings", colour=discord.Colour.dark_teal()
        )

        for key, val in settings.items():
            if setting is None or setting == key:
                embed.add_field(name=key, value=val)

        await ctx.send(embed=embed)

    @gist_settings.command(name="token")
    @commands.guild_only()
    @permissions.check_admin()
    async def settings_token(self, ctx, value: str = None):
        """
        Gets the currently set github token
        If you are an administrator you can change this value
        """

        if value is not None:
            self.change_setting(ctx.guild, "token", value)

        await self.settings_get(ctx, "token")

    @gist_settings.command(name="description")
    @commands.guild_only()
    async def settings_description(self, ctx, value: str = None):
        """
        Gets the currently set gist description
        If you are a moderator you can change this value
        """

        if value is not None:
            if mod_perm(ctx):
                self.change_setting(ctx.guild, "description", value)
            else:
                raise ManualCheckFailure(
                    content="You do not have persmissions to change the gist description"
                )

        await self.settings_get(ctx, "description")

    @gist_settings.command(name="filename")
    @commands.guild_only()
    async def settings_filename(self, ctx, value: str = None):
        """
        Gets the currently set gist filename
        If you are a moderator you can change this value
        """

        if value is not None:
            if mod_perm(ctx):
                self.change_setting(ctx.guild, "filename", value)
            else:
                raise ManualCheckFailure(
                    content="You do not have persmissions to change the gist filename"
                )

        await self.settings_get(ctx, "filename")

    @gist_settings.command(name="public")
    @commands.guild_only()
    async def settings_public(self, ctx, value: bool = None):
        """
        Gets whether gists are public and available for anyone to see
        If you are a moderator you can change this value
        """

        if value is not None:
            if mod_perm(ctx):
                self.change_setting(ctx.guild, "public", value)
            else:
                raise ManualCheckFailure(
                    content="You do not have persmissions to change whether uploaded gists are public"
                )

        await self.settings_get(ctx, "public")
