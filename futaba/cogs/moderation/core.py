#
# cogs/moderation/core.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Collection of moderation commands such as banning and muting.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import MemberConv, UserConv
from futaba.exceptions import CommandFailed, ManualCheckFailure
from futaba.navi import PunishTask, RestoreOtherRolesTask
from futaba.str_builder import StringBuilder
from futaba.utils import escape_backticks, plural, user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Moderation"]


class Moderation(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/moderation")

    def setup(self):
        pass

    @staticmethod
    def build_reason(ctx, action, minutes, reason, past=False):
        full_reason = StringBuilder(f"{action} by {user_discrim(ctx.author)}")
        if minutes:
            full_reason.write(
                f" {'for' if past else 'in'} {minutes} minute{plural(minutes)}"
            )
        if reason:
            full_reason.write(f" with reason: {reason}")
        return str(full_reason)

    async def remove_roles(self, ctx, member, minutes, action, reason):
        assert minutes

        logger.info(
            "Creating delayed role removal for '%s' (%d) with reason %r for '%s' in %d minutes",
            member.name,
            member.id,
            reason,
            action,
            minutes,
        )
        timestamp = datetime.now() + timedelta(seconds=minutes * 60)
        task = PunishTask(
            self.bot,
            None,
            ctx.author,
            timestamp,
            None,
            member=member,
            action=action
            reason=reason,
        )
        self.bot.add_tasks(task)

    async def restore_roles(self, ctx, member, minutes, reason):
        if minutes:
            logger.info(
                "Creating delayed other role addition for '%s' (%d) with reason %r in %d minutes",
                member.name,
                member.id,
                reason,
                minutes,
            )
            timestamp = datetime.now() + timedelta(seconds=minutes * 60)
            task = RestoreOtherRolesTask(
                self.bot, None, ctx.author, timestamp, member=member, reason=reason
            )
            self.bot.add_tasks(task)
        else:
            await self.bot.sql.moderation.restore_other_roles(member, reason)

    @commands.command(name="nick", aliases=["nickname", "renick"])
    @commands.guild_only()
    @permissions.check_perm("manage_nicknames")
    async def nick(self, ctx, member: MemberConv, nick: str = None):
        """ Changes or reset a member's nickname. """

        logger.info(
            "Setting the nickname of user '%s' (%d) to %r", member.name, member.id, nick
        )

        if member.top_role >= ctx.me.top_role:
            raise ManualCheckFailure("I don't have permission to nick this user")

        mod = user_discrim(ctx.author)
        await member.edit(
            nick=nick, reason=f"{mod} {'un' if nick is None else ''}set nickname"
        )

    @commands.command(name="mute", aliases=["shitpost"])
    @commands.guild_only()
    @permissions.check_perm("manage_roles")
    async def mute(self, ctx, member: MemberConv, minutes: int, *, reason: str = None):
        """
        Mutes the user for the given number of minutes.
        Requires a mute role to be configured.
        The minutes parameter must be set to a positive number.
        """

        logger.info(
            "Muting user '%s' (%d) for %d minutes", member.name, member.id, minutes
        )

        if minutes <= 0:
            # Since muting prevents members from responding or petitioning staff,
            # a timed release is mandatory. Otherwise they might be forgotten
            # and muted forever.
            raise CommandFailed()

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.mute is None:
            raise CommandFailed(content="No configured mute role")

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permission to mute this user")

        # TODO store punishment in table with task ID

        minutes = max(minutes, 0)
        reason = self.build_reason(ctx, "Muted", minutes, reason, past=True)

        await self.bot.punish.mute(guild, member, reason)

        # If a delayed event, schedule a Navi task
        if minutes:
            await self.remove_roles(ctx, member, minutes, PunishAction.RELIEVE_JAIL, reason)

    @commands.command(name="unmute", aliases=["unshitpost"])
    @commands.guild_only()
    @permissions.check_perm("manage_roles")
    async def unmute(
        self, ctx, member: MemberConv, minutes: int = 0, *, reason: str = None
    ):
        """
        Unmutes the user, with an optional delay in minutes.
        Requires a mute role to be configured.
        Set 'minutes' to 0 to unmute immediately.
        """

        logger.info(
            "Unmuting user '%s' (%d) in %d minutes", member.name, member.id, minutes
        )

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.mute is None:
            raise CommandFailed(content="No configured mute role")

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permission to unmute this user")

        # TODO store punishment in table with task ID

        minutes = max(minutes, 0)
        reason = self.build_reason(ctx, "Unmuted", minutes, reason, past=True)

        if minutes:
            await self.remove_roles(ctx, member, minutes, PunishAction.RELIEVE_MUTE, reason)
        else:
            await self.bot.punish.unjail(ctx.guild, member, reason)

    @commands.command(name="jail", aliases=["dunce"])
    @commands.guild_only()
    @permissions.check_perm("manage_roles")
    async def jail(self, ctx, member: MemberConv, minutes: int, *, reason: str = None):
        """
        Jails the user.
        Requires a jail role to be configured.
        The minutes parameter must be set to a positive number.
        """

        logger.info(
            "Jailing user '%s' (%d) for %d minutes", member.name, member.id, minutes
        )

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.jail is None:
            raise CommandFailed(content="No configured jail role")

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permission to jail this user")

        # TODO store punishment in table with task ID

        minutes = max(minutes, 0)
        reason = self.build_reason(ctx, "Jailed", minutes, reason)
        remove_other = self.bot.sql.settings.get_remove_other_roles(ctx.guild)

        if remove_other:
            self.check_other_roles(member)
            await self.bot.sql.moderation.remove_other_roles(
                member, roles.jail, full_reason
            )
        else:
            await member.add_roles(roles.jail, reason=reason)

        # If a delayed event, schedule a Navi task
        if minutes:
            await self.remove_roles(ctx, member, minutes, PunishAction.RELIEVE_JAIL, reason)

    @commands.command(name="unjail", aliases=["undunce"])
    @commands.guild_only()
    @permissions.check_perm("manage_roles")
    async def unjail(
        self, ctx, member: MemberConv, minutes: int = 0, *, reason: str = None
    ):
        """
        Removes a user from the jail.
        Requires a jail role to be configured.
        Set 'minutes' to 0 to release immediately.
        """

        logger.info(
            "Un-jailing user '%s' (%d) in %d minutes", member.name, member.id, minutes
        )

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.jail is None:
            raise CommandFailed(content="No configured jail role")

        if member.top_role > ctx.me.top_role:
            raise ManualCheckFailure("I don't have permission to unjail this user")

        # TODO store punishment in table with task ID

        minutes = max(minutes, 0)
        reason = self.build_reason(ctx, "Released", minutes, reason, past=True)

        if minutes:
            await self.remove_roles(ctx, member, minutes, PunishAction.RELIEVE_JAIL, reason)
        else:
            await self.bot.punish.unjail(ctx.guild, member, reason)

    @commands.command(name="kick")
    @commands.guild_only()
    @permissions.check_perm("kick_members")
    async def kick(self, ctx, user: UserConv, *, reason: str):
        """
        Kicks the user from the guild with a reason
        If guild has moderation logging enabled, it is logged
        """

        try:
            embed = discord.Embed(description="Done! User Kicked")
            embed.add_field(name="Reason", value=reason)

            # Don't send a journal event, that is handled by the moderation journal listener

            await ctx.guild.kick(user, reason=f"{reason} - {user_discrim(ctx.author)}")
            await ctx.send(embed=embed)

        except discord.errors.Forbidden:
            raise ManualCheckFailure(
                content="I don't have permission to kick this user"
            )

    @commands.command(name="ban")
    @commands.guild_only()
    @permissions.check_perm("ban_members")
    async def ban(self, ctx, user: UserConv, *, reason: str):
        """
        Bans the user from the guild with a reason
        If guild has moderation logging enabled, it is logged
        """

        try:
            embed = discord.Embed(description="Done! User Banned")
            embed.add_field(name="Reason", value=reason)

            # Don't send a journal event, that is handled by the moderation journal listener

            await ctx.guild.ban(
                user,
                reason=f"{reason} - {user_discrim(ctx.author)}",
                delete_message_days=1,
            )
            await ctx.send(embed=embed)

        except discord.errors.Forbidden:
            raise ManualCheckFailure(content="I don't have permission to ban this user")

    @commands.command(name="softban", aliases=["soft", "sban"])
    @commands.guild_only()
    @permissions.check_perm("ban_members")
    async def softban(self, ctx, user: UserConv, *, reason: str):
        """
        Soft-bans the user from the guild with a reason.
        If guild has moderation logging enabled, it is logged

        Soft-ban is a kick that cleans up the chat
        """

        try:
            embed = discord.Embed(description="Done! User Soft-banned")
            embed.add_field(name="Reason", value=reason)

            mod = user_discrim(ctx.author)
            banned = user_discrim(user)
            clean_reason = escape_backticks(reason)
            content = f"{mod} soft-banned {user.mention} ({banned}) with reason: `{clean_reason}`"

            # TODO add to tracker and add handler to journal event to prevent ban/softban event
            await ctx.guild.ban(user, reason=f"{reason} - {mod}", delete_message_days=1)
            await asyncio.sleep(0.1)
            await ctx.guild.unban(user, reason=f"{reason} - {mod}")
            await ctx.send(embed=embed)

            self.journal.send(
                "member/softban",
                ctx.guild,
                content,
                icon="soft",
                user=user,
                reason=reason,
                cause=ctx.author,
            )

        except discord.errors.Forbidden:
            raise ManualCheckFailure(
                content="I don't have permission to soft-ban this user"
            )

    @commands.command(name="unban", aliases=["pardon"])
    @commands.guild_only()
    @permissions.check_perm("ban_members")
    async def unban(self, ctx, user: UserConv, *, reason: str):
        """
        Unbans the id from the guild with a reason.
        If guild has moderation logging enabled, it is logged
        """

        try:
            embed = discord.Embed(description="Done! User Unbanned")
            embed.add_field(name="Reason", value=reason)

            # TODO add tracker unban event and move this to journal/impl/moderation.py
            mod = user_discrim(ctx.author)
            unbanned = user_discrim(user)
            clean_reason = escape_backticks(reason)
            content = f"{mod} unbanned {user.mention} ({unbanned}) with reason: `{clean_reason}`"

            await ctx.guild.unban(user, reason=f"{reason} - {mod}")
            await ctx.send(embed=embed)

            self.journal.send(
                "member/unban", ctx.guild, content, icon="unban", user=user
            )

        except discord.errors.Forbidden:
            raise ManualCheckFailure(
                content="I don't have permission to unban this user"
            )
