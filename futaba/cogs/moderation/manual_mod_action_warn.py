#
# cogs/moderation/manual_mod_action_warn.py
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
from datetime import datetime
from enum import Enum

from discord import AuditLogAction

from futaba.cogs.tracker import get_removal_cause
from futaba.enums import ManualModActionType, MemberLeaveType

logger = logging.getLogger(__name__)

__all__ = "ManualModActionWarn"


manual_mod_action_command_map = {
    ManualModActionType.SPECIAL_ROLE_MUTE: "{prefix}mute",
    ManualModActionType.SPECIAL_ROLE_JAIL: "{prefix}jail or {prefix}dunce",
    ManualModActionType.KICK_MEMBER: "{prefix}kick",
    ManualModActionType.BAN_MEMBER: "{prefix}ban",
}


class ManualModActionWarn:
    """
    Warn moderators when they invoke a mod action manually.
    """

    __slots__ = ("bot",)

    def __init__(self, bot):
        self.bot = bot

    async def dispatch_manual_action_warning(
        self, guild, action, moderator, target, **kwargs
    ):
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

        prefix = self.bot.prefix(guild)

        if action in (
            ManualModActionType.SPECIAL_ROLE_GUEST,
            ManualModActionType.SPECIAL_ROLE_MEMBER,
        ):
            detail_message = "This role should be entirely automated by the bot."
        elif action in (
            ManualModActionType.SPECIAL_ROLE_MUTE,
            ManualModActionType.SPECIAL_ROLE_JAIL,
        ):
            role = kwargs["role"]

            command = manual_mod_action_command_map[action].format(prefix=prefix)
            detail_message = (
                f"In the future, use the command {command} to add "
                f"or remove the {action.value} role '{role.name}'."
            )
        else:
            command = manual_mod_action_command_map[action].format(prefix=prefix)
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
            special_roles.member_role: ManualModActionType.SPECIAL_ROLE_MEMBER,
            special_roles.guest_role: ManualModActionType.SPECIAL_ROLE_GUEST,
            special_roles.mute_role: ManualModActionType.SPECIAL_ROLE_MUTE,
            special_roles.jail_role: ManualModActionType.SPECIAL_ROLE_JAIL,
        }

        for (role, moderator) in manually_updated_roles:
            action = special_role_name_action_map[role]
            await self.dispatch_manual_action_warning(
                member.guild, action, moderator, member, role=role
            )

    _audit_log_to_manual_mod_action_map = {
        MemberLeaveType.KICKED: ManualModActionType.KICK_MEMBER,
        MemberLeaveType.BANNED: ManualModActionType.BAN_MEMBER,
    }

    async def member_remove(self, member):
        if not self.bot.sql.settings.get_warn_manual_mod_action(member.guild):
            return

        leave_reason = await get_removal_cause(member, datetime.now())

        if leave_reason not in (MemberLeaveType.KICKED, MemberLeaveType.BANNED):
            return

        mod_action = self._audit_log_to_manual_mod_action_map[leave_reason.type]
        await self.dispatch_manual_action_warning(
            member.guild, mod_action, leave_reason.cause, leave_reason.member
        )
