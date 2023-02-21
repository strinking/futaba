#
# cogs/settings/core.py
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
Cog for all commands that change bot settings. It ensures persistence
of configured settings in between runs of the bot.
"""

import logging
import re
from itertools import chain
from typing import Union

import discord
from discord.ext import commands

from futaba import permissions
from futaba.converters import MemberConv, RoleConv, TextChannelConv
from futaba.emojis import ICONS
from futaba.exceptions import CommandFailed, ManualCheckFailure, SendHelp
from futaba.permissions import admin_perm, mod_perm
from futaba.str_builder import StringBuilder
from futaba.utils import plural
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["Settings"]


class Settings(AbstractCog):
    __slots__ = ("journal",)

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/settings")

    def setup(self):
        for guild in self.bot.guilds:
            self.bot.sql.settings.get_special_roles(guild)
            self.bot.sql.settings.get_reapply_roles(guild)

    @commands.command(name="prefix")
    async def prefix(self, ctx, *, prefix: str = None):
        """
        Gets the current prefix. If you're a moderator, you can set it too.
        A trailing underscore is converted into spaces. A single '_' unsets
        the bot's prefix, and uses the default one.
        """

        if prefix is None:
            # Get prefix
            bot_prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            if ctx.guild is None:
                embed.description = "No command prefix, all messages are commands"
            else:
                embed.description = f"Prefix for {ctx.guild.name} is `{bot_prefix}`"
        elif ctx.guild is None and prefix is not None:
            # Attempt to set prefix outside of guild
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = "Cannot set a command prefix outside of a server!"
            raise CommandFailed(embed=embed)
        elif not mod_perm(ctx):
            # Lacking authority to set prefix
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = "You do not have permission to set the prefix"
            raise ManualCheckFailure(embed=embed)
        elif prefix == "_":
            # Unset prefix
            with self.bot.sql.transaction():
                self.bot.sql.settings.set_prefix(ctx.guild, None)
                bot_prefix = self.bot.prefix(ctx.guild)

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = (
                f"Unset prefix for {ctx.guild.name}. (Default prefix: `{bot_prefix}`)"
            )
            self.journal.send(
                "prefix",
                ctx.guild,
                "Unset bot command prefix",
                icon="settings",
                prefix=None,
                default_prefix=self.bot.config.default_prefix,
            )
        else:
            # Set prefix
            bot_prefix = re.sub(r"_$", " ", prefix)
            with self.bot.sql.transaction():
                self.bot.sql.settings.set_prefix(ctx.guild, bot_prefix)

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = f"Set prefix for {ctx.guild.name} to `{bot_prefix}`"
            self.journal.send(
                "prefix",
                ctx.guild,
                "Unset bot command prefix",
                icon="settings",
                prefix=bot_prefix,
                default_prefix=self.bot.config.default_prefix,
            )

        await ctx.send(embed=embed)

    @commands.command(name="maxdelete", aliases=["maxdeletemsg"])
    @commands.guild_only()
    async def max_delete(self, ctx, count: int = None):
        """
        Gets the current setting for maximum messages to bulk delete.
        If you're an administrator, you can change this value.
        """

        if count is None:
            # Get max delete messages
            max_delete_messages = self.bot.sql.settings.get_max_delete_messages(
                ctx.guild
            )
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = f"Maximum number of messages that can be deleted in bulk is `{max_delete_messages}`"
        elif not admin_perm(ctx):
            # Lacking authority to set max delete messages
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                "You do not have permission to set the maximum deletable messages"
            )
            raise ManualCheckFailure(embed=embed)
        elif count <= 0:
            # Negative value
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = "This value must be a positive, non-zero integer"
            raise CommandFailed(embed=embed)
        elif count >= 2**32 - 1:
            # Over a sane upper limit
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                "This value is way too high. Try a more reasonable value."
            )
            raise CommandFailed(embed=embed)
        else:
            # Set max delete messages
            with self.bot.sql.transaction():
                self.bot.sql.settings.set_max_delete_messages(ctx.guild, count)

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = f"Set maximum deletable messages to `{count}`"

        await ctx.send(embed=embed)

    @commands.command(name="warnmanual")
    @commands.guild_only()
    async def warn_manual_mod_action(self, ctx, value: bool = None):
        """
        Gets the current setting for warning about manual mod actions.
        If you're an administrator, you can change this value.
        """

        if value is None:
            warn_manual_mod_action = self.bot.sql.settings.get_warn_manual_mod_action(
                ctx.guild
            )
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            state = "enabled" if warn_manual_mod_action else "disabled"
            embed.description = f"Warning moderators about performing mod actions manually is **{state}**"
        elif not admin_perm(ctx):
            # Lacking authority to set warn manual mod action
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = "You do not have permission to enable or disable manual mod action warning"
            raise ManualCheckFailure(embed=embed)
        else:
            with self.bot.sql.transaction():
                self.bot.sql.settings.set_warn_manual_mod_action(ctx.guild, value)

            embed = discord.Embed(colour=discord.Colour.teal())
            embed.description = f"Set warning moderators about performing mod actions manually to `{value}`"

        await ctx.send(embed=embed)

    @commands.command(name="removeother", aliases=["rmother"])
    @commands.guild_only()
    async def remove_other_roles_on_punish(self, ctx, value: bool = None):
        """
        Gets the current setting for whether punishment actions remove all other roles, or leaves them.
        If you're an administrator, you can change this value.
        """

        if value is None:
            remove_other_roles = self.bot.sql.settings.get_remove_other_roles(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            state = "are removed" if remove_other_roles else "are kept"
            embed.description = (
                f"When punishment roles are added other roles **{state}**"
            )
        elif not admin_perm(ctx):
            # Lacking authority to set remove other roles
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = "You do not have permissions to change the removal of non-punishment roles"
            raise ManualCheckFailure(embed=embed)
        else:
            with self.bot.sql.transaction():
                self.bot.sql.settings.set_remove_other_roles(ctx.guild, value)

            embed = discord.Embed(colour=discord.Colour.teal())
            embed.description = (
                f"Set removal of other non-punishment roles to `{value}`"
            )

        await ctx.send(embed=embed)

    @commands.command(name="specroles", aliases=["sroles"])
    @commands.guild_only()
    async def special_roles(self, ctx):
        """Retrieves all configured roles for this guild."""

        logger.info(
            "Sending list of all configured roles for guild '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        def mention(role):
            return getattr(role, "mention", "(none)")

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = "\n".join(
            (
                f'{ICONS["member"]} Member: {mention(roles.member)}',
                f'{ICONS["guest"]} Guest: {mention(roles.guest)}',
                f'{ICONS["mute"]} Mute: {mention(roles.mute)}',
                f'{ICONS["jail"]} Jail: {mention(roles.jail)}',
                f'{ICONS["focus"]} Focus: {mention(roles.focus)}',
            )
        )
        await ctx.send(embed=embed)

    async def check_role(self, ctx, role):
        embed = discord.Embed(colour=discord.Colour.red())
        if role.is_default():
            embed.description = "@everyone role cannot be assigned for this purpose"
            raise CommandFailed(embed=embed)

        special_roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if role in special_roles:
            embed.description = "Cannot assign the same role for multiple purposes"
            raise CommandFailed(embed=embed)

        embed = permissions.elevated_role_embed(ctx.guild, role, "warning")
        if embed is not None:
            await ctx.send(embed=embed)

    @commands.command(name="setmember")
    @commands.guild_only()
    @permissions.check_mod()
    async def set_member_role(self, ctx, *, role: RoleConv = None):
        """Set the member role for this guild. No argument to unset."""

        logger.info(
            "Setting member role for guild '%s' (%d) to '%s'",
            ctx.guild.name,
            ctx.guild.id,
            role,
        )

        if role is not None:
            await self.check_role(ctx, role)

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, member=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f"Set member role to {role.mention}"
            content = f"Set member role to {role.mention}"
        else:
            embed.description = "Unset member role"
            content = "Unset the member role"

        await ctx.send(embed=embed)
        self.journal.send(
            "roles/member", ctx.guild, content, icon="settings", role=role
        )

    @commands.command(name="setguest")
    @commands.guild_only()
    @permissions.check_mod()
    async def set_guest_role(self, ctx, *, role: RoleConv = None):
        """Set the guest role for this guild. No argument to unset."""

        logger.info(
            "Setting guest role for guild '%s' (%d) to '%s'",
            ctx.guild.name,
            ctx.guild.id,
            role,
        )

        if role is not None:
            await self.check_role(ctx, role)

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, guest=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f"Set guest role to {role.mention}"
            content = f"Set the guest role to {role.mention}"
        else:
            embed.description = "Unset guest role"
            content = "Unset the guest role"

        await ctx.send(embed=embed)
        self.journal.send("roles/guest", ctx.guild, content, icon="settings", role=role)

    @commands.command(name="setmute")
    @commands.guild_only()
    @permissions.check_mod()
    async def set_mute_role(self, ctx, *, role: RoleConv = None):
        """Set the mute role for this guild. No argument to unset."""

        logger.info(
            "Setting mute role for guild '%s' (%d) to '%s'",
            ctx.guild.name,
            ctx.guild.id,
            role,
        )

        if role is not None:
            await self.check_role(ctx, role)

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, mute=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f"Set mute role to {role.mention}"
            content = f"Set the mute role to {role.mention}"
        else:
            embed.description = "Unset mute role"
            content = "Unset the mute role"

        await ctx.send(embed=embed)
        self.journal.send("roles/mute", ctx.guild, content, icon="settings", role=role)

    @commands.command(name="setjail")
    @commands.guild_only()
    @permissions.check_mod()
    async def set_jail_role(self, ctx, *, role: RoleConv = None):
        """Set the mute role for this guild. No argument to unset."""

        logger.info(
            "Setting mute role for guild '%s' (%d) to '%s'",
            ctx.guild.name,
            ctx.guild.id,
            role,
        )

        if role is not None:
            await self.check_role(ctx, role)

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, jail=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f"Set jail role to {role.mention}"
            content = f"Set the jail role to {role.mention}"
        else:
            embed.description = "Unset jail role"
            content = "Unset the jail role"

        await ctx.send(embed=embed)
        self.journal.send("roles/jail", ctx.guild, content, icon="settings", role=role)

    @commands.command(name="setfocus")
    @commands.guild_only()
    @permissions.check_mod()
    async def set_focus_role(self, ctx, *, role: RoleConv = None):
        """Set the focus role for this guild. No argument to unset."""

        logger.info(
            "Setting focus role for guild '%s' (%d) to '%s'",
            ctx.guild.name,
            ctx.guild.id,
            role,
        )

        if role is not None:
            await self.check_role(ctx, role)

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, focus=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f"Set focus role to {role.mention}"
            content = f"Set the focus role to {role.mention}"
        else:
            embed.description = "Unset focus role"
            content = "Unset the focus role"

        await ctx.send(embed=embed)
        self.journal.send("roles/focus", ctx.guild, content, icon="settings", role=role)

    @commands.command(name="setnonpurge")
    @commands.guild_only()
    @permissions.check_mod()
    async def set_nonpurge_role(self, ctx, *, role: RoleConv = None):
        """Set the nonpurge role for this guild. No argument to unset."""

        logger.info(
            "Setting nonpurge role for guild '%s' (%d) to '%s'",
            ctx.guild.name,
            ctx.guild.id,
            role,
        )

        if role is not None:
            await self.check_role(ctx, role)

        with self.bot.sql.transaction():
            self.bot.sql.settings.set_special_roles(ctx.guild, nonpurge=role)

        embed = discord.Embed(colour=discord.Colour.green())
        if role:
            embed.description = f"Set nonpurge role to {role.mention}"
            content = f"Set the nonpurge role to {role.mention}"
        else:
            embed.description = "Unset nonpurge role"
            content = "Unset the nonpurge role"

        await ctx.send(embed=embed)
        self.journal.send(
            "roles/nonpurge", ctx.guild, content, icon="settings", role=role
        )

    @commands.group(name="reapply", aliases=["reapp"])
    @commands.guild_only()
    async def reapply(self, ctx):
        """Manages settings related to automatic role reapplication."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @reapply.command(name="add", aliases=["append", "extend", "new", "register", "set"])
    @commands.guild_only()
    async def reapply_add(self, ctx, *roles: RoleConv):
        """
        Designate a collection of roles as "reappliable".
        Reappliable roles, in addition to all punishment and self-assignable roles, are
        automatically reapplied when the member rejoins the guild.
        """

        warning = StringBuilder()
        roles = set(roles)

        # Filter out roles that shouldn't be reassignable
        special_roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        if ctx.guild.default_role in roles:
            warning.writeln("You should not make @everyone reappliable.")
            roles.remove(ctx.guild.default_role)

        if special_roles.guest_role in roles:
            warning.writeln(
                f"You should not make {special_roles.guest_role.mention} reappliable."
            )
        if special_roles.member_role in roles:
            warning.writeln(
                f"You should not make {special_roles.member_role.mention} reappliable."
            )

        # Warn on roles that are already reappliable
        if special_roles.mute_role in roles:
            warning.writeln(
                f"The {special_roles.mute_role.mention} is always reappliable."
            )
        if special_roles.jail_role in roles:
            warning.writeln(
                f"The {special_roles.jail_role.mention} is always reappliable."
            )

        if "SelfAssignableRoles" in self.bot.cogs:
            assignable_roles = self.bot.sql.roles.get_assignable_roles(ctx.guild)
        else:
            assignable_roles = ()

        for role in roles:
            if role in assignable_roles:
                warning.writeln(
                    f"The {role.mention} is already reappliable since it is self-assignable."
                )

        if warning:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = str(warning)
            await ctx.send(embed=embed)

        logger.info(
            "Setting roles as 'reappliable': [%s]",
            ", ".join(role.name for role in roles),
        )

        with self.bot.sql.transaction():
            self.bot.sql.settings.update_reapply_roles(ctx.guild, roles, True)

    @reapply.command(
        name="remove", aliases=["rm", "delete", "del", "unregister", "unset"]
    )
    @commands.guild_only()
    async def reapply_remove(self, ctx, *roles: RoleConv):
        """
        Remove the designation of the given roles as "reappliable".
        Reappliable roles, in addition to all punishment and self-assignable roles, are
        automatically reapplied when the member rejoins the guild.
        """

        logger.info(
            "Unsetting roles as 'reappliable': [%s]",
            ", ".join(role.name for role in roles),
        )

        with self.bot.sql.transaction():
            self.bot.sql.settings.update_reapply_roles(ctx.guild, set(roles), False)

    @reapply.command(name="show", aliases=["display", "list", "ls"])
    @commands.guild_only()
    async def reapply_show(self, ctx):
        """
        Lists all roles that are reappliable.
        Reappliable roles, in addition to all punishment and self-assignable roles, are
        automatically reapplied when the member rejoins the guild.
        """

        reapply_roles = self.bot.sql.settings.get_reapply_roles(ctx.guild)
        special_roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        descr = StringBuilder(sep=", ")
        has_roles = False

        # Manually set
        for role in sorted(reapply_roles, key=lambda r: r.name):
            descr.write(role.mention)
        if descr:
            embed.add_field(name="Manually designated", value=str(descr))
            has_roles = True
        else:
            embed.add_field(name="Manually designated", value="(none)")

        # Punishment roles
        descr.clear()
        if special_roles.mute_role is not None:
            descr.write(special_roles.mute_role.mention)
        if special_roles.jail_role is not None:
            descr.write(special_roles.jail_role.mention)
        if descr:
            embed.add_field(name="Punishment roles", value=str(descr))
            has_roles = True

        # Self-assignable roles
        if "SelfAssignableRoles" in self.bot.cogs:
            assignable_roles = self.bot.sql.roles.get_assignable_roles(ctx.guild)
            if assignable_roles:
                embed.add_field(
                    name="Self-assignable roles",
                    value=", ".join(
                        role.mention
                        for role in sorted(assignable_roles, key=lambda r: r.name)
                    ),
                )
                has_roles = True

        # Send final embed
        if has_roles:
            embed.title = "\N{MILITARY MEDAL} Roles which are automatically reapplied"
        else:
            embed.colour = discord.Colour.dark_purple()

        await ctx.send(embed=embed)

    @reapply.command(name="auto", aliases=["automatic"])
    @commands.guild_only()
    async def reapply_auto(self, ctx, value: bool = None):
        """
        Tells whether automatic role reapplication is enabled.
        Only self-assignable and punishment roles are re-applied.
        If you're an administrator, you can change this value.
        """

        if value is None:
            # Get reapplication roles
            reapply = self.bot.sql.settings.get_auto_reapply(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            enabled = "enabled" if reapply else "disabled"
            embed.description = (
                f"Automatic role reapplication is **{enabled}** on this server"
            )
        elif not admin_perm(ctx):
            # Lacking authority to set reapplication
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                "You do not have permission to set automatic role reapplication"
            )
            raise ManualCheckFailure(embed=embed)
        else:
            # Set role reapplication
            with self.bot.sql.transaction():
                self.bot.sql.settings.set_auto_reapply(ctx.guild, value)

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = (
                f"{'Enabled' if value else 'Disabled'} automatic role reapplication"
            )

        await ctx.send(embed=embed)

    @commands.command(name="mentionprefix", aliases=["mprefix", "menpfx"])
    @commands.guild_only()
    async def mentionable_prefix(self, ctx, value: int = None):
        """
        Gets the current number of typeable characters required for your mention.
        If you're a moderator, you can change this value. (Set to 0 to disable)
        """

        if value is None:
            # Get prefix
            value = self.bot.sql.settings.get_mentionable_name_prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = (
                f"Names must begin with at least {value} typeable character{plural(value)}"
                if value
                else "No guild requirement for mentionable names"
            )
        elif not mod_perm(ctx):
            # Lacking authority to set mentionable prefix
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                "You do not have permission to set the mentionable name prefix"
            )
            raise ManualCheckFailure(embed=embed)
        else:
            # Set prefix
            if value < 0 or value > 32:
                embed = discord.Embed()
                embed.colour = discord.Colour.red()
                embed.description = "Prefix lengths must be between `0` and `32`."
                raise CommandFailed(embed=embed)

            with self.bot.sql.transaction():
                self.bot.sql.settings.set_mentionable_name_prefix(ctx.guild, value)

            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = (
                f"Set mentionable prefix to {value} character{plural(value)}"
                if value
                else "Disabled mentionable prefix requirement"
            )

        await ctx.send(embed=embed)

    @commands.group(name="trackerblacklist", aliases=["trackerbl", "trkbl"])
    @commands.guild_only()
    async def tracker_blacklist(self, ctx):
        """Manages tracker blacklist entries for this guild."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @tracker_blacklist.command(name="add", aliases=["append", "extend"])
    @commands.guild_only()
    @permissions.check_mod()
    async def tracker_blacklist_add(
        self, ctx, *, user_or_channel: Union[MemberConv, TextChannelConv]
    ):
        """Add a user or channel to the tracking blacklist."""

        logger.info(
            "Adding %s '%s' (%d) to the tracking blacklist for guild '%s' (%d)",
            "user" if isinstance(user_or_channel, discord.abc.User) else "channel",
            user_or_channel.name,
            user_or_channel.id,
            ctx.guild.name,
            ctx.guild.id,
        )

        with self.bot.sql.transaction():
            self.bot.sql.settings.add_to_tracking_blacklist(ctx.guild, user_or_channel)

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = f"Added {user_or_channel.mention} to the tracking blacklist"

        await ctx.send(embed=embed)

    @tracker_blacklist.command(name="remove", aliases=["rm", "delete", "del"])
    @commands.guild_only()
    @permissions.check_mod()
    async def tracker_blacklist_remove(
        self, ctx, *, user_or_channel: Union[MemberConv, TextChannelConv]
    ):
        """Remove a user or channel from the tracking blacklist."""

        logger.info(
            "Removing %s '%s' (%d) from the tracking blacklist for guild '%s' (%d)",
            "user" if isinstance(user_or_channel, discord.abc.User) else "channel",
            user_or_channel.name,
            user_or_channel.id,
            ctx.guild.name,
            ctx.guild.id,
        )

        with self.bot.sql.transaction():
            self.bot.sql.settings.remove_from_tracking_blacklist(
                ctx.guild, user_or_channel
            )

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = (
            f"Removed {user_or_channel.mention} from the tracking blacklist"
        )

        await ctx.send(embed=embed)

    @tracker_blacklist.command(name="show", aliases=["display", "list"])
    @commands.guild_only()
    @permissions.check_mod()
    async def tracker_blacklist_show(self, ctx):
        """Shows all blacklist entries for this guild."""

        blacklist = self.bot.sql.settings.get_tracking_blacklist(ctx.guild)

        if not blacklist.blacklisted_users and not blacklist.blacklisted_channels:
            prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.set_author(name="No blacklist entries")
            embed.description = (
                f"Moderators can use the `{prefix}trackerblacklist add/remove` "
                "commands to change this list!"
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name="Blacklist entries")

        if blacklist.blacklisted_channels:
            channel_msg = StringBuilder(sep=", ")
            for channel_id in blacklist.blacklisted_channels:
                channel = discord.utils.get(ctx.guild.channels, id=channel_id)
                channel_msg.write(channel.mention)

            embed.add_field(name="Blacklisted channels", value=channel_msg)

        if blacklist.blacklisted_users:
            user_msg = StringBuilder(sep=", ")
            for user_id in blacklist.blacklisted_users:
                user = discord.utils.get(
                    chain(ctx.guild.members, ctx.bot.users), id=user_id
                )
                user_msg.write(user.mention)

            embed.add_field(name="Blacklisted channels", value=user_msg)

        await ctx.send(embed=embed)
