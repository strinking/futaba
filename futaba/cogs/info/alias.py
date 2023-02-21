#
# cogs/info/alias.py
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
Tracking for aliases of members, storing previous usernames, nicknames, and avatars.
"""

import logging
import re
from datetime import datetime
from io import BytesIO

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import UserConv
from futaba.exceptions import CommandFailed, SendHelp
from futaba.str_builder import StringBuilder
from futaba.utils import fancy_timedelta, user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Alias"]

EXTENSION_REGEX = re.compile(r"/\w+\.(\w+)(?:\?.+)?$")


class MemberChanges:
    __slots__ = ("avatar_url", "username", "nickname")

    def __init__(self):
        self.avatar_url = None
        self.username = None
        self.nickname = None

    def __bool__(self):
        for field in self.__slots__:
            if getattr(self, field) is not None:
                return True
        return False


class Alias(AbstractCog):
    """
    Cog for member alias information.
    """

    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/alias")

    def setup(self):
        pass

    async def member_update(self, before, after):
        """Handles update of member information."""

        changes = MemberChanges()
        timestamp = datetime.now()

        if before.avatar != after.avatar:
            logger.info(
                "Member '%s' (%d) has changed their profile picture (%s)",
                before.name,
                before.id,
                after.avatar,
            )
            changes.avatar_url = after.avatar_url

        if before.name != after.name:
            logger.info(
                "Member '%s' (%d) has changed name to '%s'",
                before.name,
                before.id,
                after.name,
            )
            changes.username = after.name

        if before.nick != after.nick and after.nick is not None:
            logger.info(
                "Member '%s' (%d) has changed nick to '%s'",
                before.display_name,
                before.id,
                after.nick,
            )
            changes.nickname = after.nick

        # Check if there were any changes
        if not changes:
            return

        attrs = StringBuilder(sep=", ")
        with self.bot.sql.transaction():
            if changes.avatar_url is not None:
                avatar, avatar_ext = await self._download_avatar(changes.avatar_url)
                self.bot.sql.alias.add_avatar(before, timestamp, avatar, avatar_ext)
                attrs.write(f"avatar: {changes.avatar_url}")
            if changes.username is not None:
                self.bot.sql.alias.add_username(before, timestamp, changes.username)
                attrs.write(f"name: {changes.username}")
            if changes.nickname is not None:
                self.bot.sql.alias.add_nickname(before, timestamp, changes.nickname)
                attrs.write(f"nick: {changes.nickname}")

        content = f"{user_discrim(before)} updated {attrs}"
        self.journal.send(
            "member/update",
            before.guild,
            content,
            icon="person",
            before=before,
            after=after,
            changes=changes,
        )

    async def _download_avatar(self, asset):
        avatar = BytesIO()
        avatar_url = str(asset)
        await asset.save(avatar)

        match = EXTENSION_REGEX.findall(avatar_url)
        if not match:
            raise ValueError(f"Avatar URL does not match extension regex: {avatar_url}")

        avatar_ext = match[0]
        return avatar, avatar_ext

    @commands.command(name="aliases")
    async def aliases(self, ctx, *, user: UserConv):
        """Gets information about known aliases of the given user."""

        logger.info(
            "Getting and printing alias information for some user '%s' (%d)",
            user.name,
            user.id,
        )

        avatars, usernames, nicknames, alt_user_ids = self.bot.sql.alias.get_aliases(
            ctx.guild, user
        )

        # Remove self from chain
        try:
            alt_user_ids.remove(user.id)
        except KeyError:
            pass

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Member alias information")

        if not any((avatars, usernames, nicknames, alt_user_ids)):
            embed.colour = discord.Colour.dark_purple()
            embed.description = f"No information found for {user.mention}"

            await ctx.send(embed=embed)
            return

        embed.description = f"{user.mention}\n"
        content = StringBuilder()
        files = []

        if avatars:
            for i, (avatar_bin, avatar_ext, timestamp) in enumerate(avatars, 1):
                time_since = fancy_timedelta(timestamp)
                content.writeln(f"**{i}.** set {time_since} ago")
                files.append(
                    discord.File(
                        avatar_bin, filename=f"avatar {time_since}.{avatar_ext}"
                    )
                )
            embed.add_field(name="Past avatars", value=str(content))
            content.clear()

        if usernames:
            for username, timestamp in usernames:
                content.writeln(f"- `{username}` set {fancy_timedelta(timestamp)} ago")
            embed.add_field(name="Past usernames", value=str(content))
            content.clear()

        if nicknames:
            for nickname, timestamp in nicknames:
                content.writeln(f"- `{nickname}` set {fancy_timedelta(timestamp)} ago")
            embed.add_field(name="Past nicknames", value=str(content))
            content.clear()

        if alt_user_ids:
            for alt_user_id in alt_user_ids:
                content.writeln(f"<@!{alt_user_id}>")
            embed.add_field(name="Possible alts", value=str(content))

        await ctx.send(embed=embed)
        for i, file in enumerate(files, 1):
            await ctx.send(content=f"#{i}", file=file)

    @commands.group(name="alts", aliases=["alt", "alias"])
    @commands.guild_only()
    async def alts(self, ctx):
        """Manages the list of suspected alternate accounts."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @alts.command(name="add", aliases=["append", "extend", "new", "register"])
    @commands.guild_only()
    @permissions.check_mod()
    async def add_alt(self, ctx, first_user: UserConv, second_user: UserConv):
        """Add a suspected alternate account for a user."""

        logger.info(
            "Adding suspected alternate account pair for '%s' (%d) and '%s' (%d)",
            first_user.name,
            first_user.id,
            second_user.name,
            second_user.id,
        )

        if first_user == second_user:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = "Both users are the same person!"
            raise CommandFailed(embed=embed)

        with self.bot.sql.transaction():
            self.bot.sql.alias.add_possible_alt(ctx.guild, first_user, second_user)

        content = f"Added {first_user.mention} and {second_user.mention} as possible alt accounts."
        self.journal.send(
            "alt/add",
            ctx.guild,
            content,
            icon="item_add",
            users=[first_user, second_user],
        )

    @alts.command(name="delchain")
    @commands.guild_only()
    @permissions.check_mod()
    async def del_alt_chain(self, ctx, user: UserConv):
        """Removes all suspected alternate accounts for a user."""

        with self.bot.sql.transaction():
            self.bot.sql.alias.all_delete_possible_alts(ctx.guild, user)

        content = f"Removed all alt accounts in {user.mention}'s chain"
        self.journal.send("alt/clear", ctx.guild, content, icon="item_clear", user=user)
