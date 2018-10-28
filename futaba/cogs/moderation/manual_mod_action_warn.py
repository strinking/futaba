#
# cogs/moderation/manual_modaction_warn.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

"""
Cog to warn when a mod action is done manually, instead of through the bot.
"""
import logging
from enum import Enum

from discord import AuditLogAction

logger = logging.getLogger(__name__)

__all__ = "ManualModActionWarn"


class ManualModActionType(Enum):
    special_role_member = "member"
    special_role_guest = "guest"
    special_role_mute = "mute"
    special_role_jail = "jail"
    kick_member = "kick"
    ban_member = "ban"


manual_mod_action_command_map = {
    ManualModActionType.special_role_mute: "!mute",
    ManualModActionType.special_role_jail: "!jail or !dunce",
    ManualModActionType.kick_member: "!kick",
    ManualModActionType.ban_member: "!ban",
}


class ManualModActionWarn:
    """
    Warn moderators when they invoke a mod action manually.
    """

    __slots__ = ("bot",)

    def __init__(self, bot):
        self.bot = bot

    async def dispatch_manual_action_warning(self, action, moderator, target, **kwargs):
        """Dispatch a warning about invoking a moderation action manually."""

        logger.info(
            "Moderator '%s' (%d) completed a moderation action (%s) manually on member: '%s' (%d)",
            moderator.name,
            moderator.id,
            action.name,
            target.name,
            target.id,
        )

        message_template = """
 Hey, it looks like you did some moderation action manually when you could have used the bot.

{detail_message}
 """.strip()
        if action in {
            ManualModActionType.special_role_guest,
            ManualModActionType.special_role_member,
        }:
            detail_message = "This role should be entirely automated by the bot."
        elif action in {
            ManualModActionType.special_role_mute,
            ManualModActionType.special_role_jail,
        }:
            role = kwargs["role"]

            command = manual_mod_action_command_map[action]
            detail_message = (
                f"In the future, use the command {command} to add "
                f"or remove the {action.value} role '{role.name}'."
            )
        else:
            command = manual_mod_action_command_map[action]
            detail_message = (
                f"In the future, use the command {command} to {action.value} a member."
            )

        final_message = message_template.format(detail_message=detail_message)

        await moderator.send(final_message)

    async def find_manually_updated_roles(self, member, roles):
        """Finds which roles were manually updated by a moderator.

        Takes a member and an iterable of roles to check.

        Returns a list of tuples containing the role and moderator that updated the role on the member.
        """
        roles = set(roles)

        updated_roles = []

        async for entry in member.guild.audit_logs(
            limit=20, action=AuditLogAction.member_role_update
        ):
            if entry.target != member:
                continue

            if entry.user == self.bot.user:
                continue

            roles_updated_here = roles & (
                set(entry.before.roles) | set(entry.after.roles)
            )

            roles -= roles_updated_here

            updated_roles.extend((role, entry.user) for role in roles_updated_here)

        return updated_roles

    async def member_update(self, before, after):
        member = after
        after_roles = set(after.roles)
        before_roles = set(before.roles)

        roles_updated = after_roles ^ before_roles

        if not roles_updated:
            return

        if not self.bot.sql.settings.get_warn_manual_mod_action(member.guild):
            return

        special_roles = self.bot.sql.settings.get_special_roles(member.guild)
        roles_to_check = roles_updated & set(special_roles)

        if not roles_to_check:
            return

        manually_updated_roles = await self.find_manually_updated_roles(
            member, roles_to_check
        )

        special_role_name_action_map = {
            special_roles.member_role: ManualModActionType.special_role_member,
            special_roles.guest_role: ManualModActionType.special_role_guest,
            special_roles.mute_role: ManualModActionType.special_role_mute,
            special_roles.jail_role: ManualModActionType.special_role_jail,
        }

        for (role, moderator) in manually_updated_roles:
            action = special_role_name_action_map[role]
            await self.dispatch_manual_action_warning(
                action, moderator, member, role=role
            )

    async def find_manually_removed_member(self, member):
        """Finds a possibly manually kicked or banned member.

        Returns a tuple: (remove_type, member, moderator) upon the user being manually banned,
            otherwise returns None. (where remove_type is either AuditLogAction.kick or AuditLogAction.ban)
        """

        async for entry in member.guild.audit_logs(limit=20):
            if entry.action not in {AuditLogAction.ban, AuditLogAction.kick}:
                continue

            if entry.target != member:
                continue

            if entry.user == self.bot.user:
                continue

            return (entry.action, member, entry.user)

    _audit_log_to_manual_mod_action_map = {
        AuditLogAction.kick: ManualModActionType.kick_member,
        AuditLogAction.ban: ManualModActionType.ban_member,
    }

    async def member_remove(self, member):
        possible_manual_action = await self.find_manually_removed_member(member)

        if possible_manual_action is None:
            return

        if not self.bot.sql.settings.get_warn_manual_mod_action(member.guild):
            return

        (action, member, moderator) = possible_manual_action

        mod_action = self._audit_log_to_manual_mod_action_map[action]
        await self.dispatch_manual_action_warning(mod_action, moderator, member)
