#
# sql/data/settings.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging

import discord

from futaba.enums import LocationType
from futaba.utils import partition_on

logger = logging.getLogger(__name__)


class GuildSettingsData:
    __slots__ = (
        "prefix",
        "max_delete_messages",
        "warn_manual_mod_action",
        "remove_other_roles",
        "mentionable_name_prefix",
    )

    def __init__(
        self,
        prefix,
        max_delete_messages,
        *,
        warn_manual_mod_action,
        remove_other_roles,
        mentionable_name_prefix,
    ):
        self.prefix = prefix
        self.max_delete_messages = max_delete_messages
        self.warn_manual_mod_action = warn_manual_mod_action
        self.remove_other_roles = remove_other_roles
        self.mentionable_name_prefix = mentionable_name_prefix


class ReapplyRolesData:
    __slots__ = ("roles", "auto_reapply")

    def __init__(self, roles, auto_reapply):
        self.roles = roles
        self.auto_reapply = auto_reapply


class SpecialRoleData:
    __slots__ = (
        "guild",
        "member_role",
        "guest_role",
        "mute_role",
        "jail_role",
        "focus_role",
        "nonpurge_role",
    )

    def __init__(
        self,
        guild,
        member_role_id,
        guest_role_id,
        mute_role_id,
        jail_role_id,
        focus_role_id,
        nonpurge_role_id,
    ):
        self.guild = guild
        self.member_role = self._get_role(member_role_id)
        self.guest_role = self._get_role(guest_role_id)
        self.mute_role = self._get_role(mute_role_id)
        self.jail_role = self._get_role(jail_role_id)
        self.focus_role = self._get_role(focus_role_id)
        self.nonpurge_role = self._get_role(nonpurge_role_id)

    def update(self, attrs):
        logger.debug("Updating special role storage: %s", attrs)
        if "member" in attrs:
            self.member_role = attrs["member"]
        if "guest" in attrs:
            self.guest_role = attrs["guest"]
        if "mute" in attrs:
            self.mute_role = attrs["mute"]
        if "jail" in attrs:
            self.jail_role = attrs["jail"]
        if "focus" in attrs:
            self.focus_role = attrs["focus"]
        if "nonpurge" in attrs:
            self.nonpurge_role = attrs["nonpurge"]

    @property
    def member(self):
        return self.member_role

    @property
    def guest(self):
        return self.guest_role

    @property
    def mute(self):
        return self.mute_role

    @property
    def jail(self):
        return self.jail_role

    @property
    def focus(self):
        return self.focus_role

    @property
    def nonpurge(self):
        return self.nonpurge_role

    def _get_role(self, id):
        if id is None:
            return None

        return discord.utils.get(self.guild.roles, id=id)

    def __iter__(self):
        yield self.member_role
        yield self.guest_role
        yield self.mute_role
        yield self.jail_role
        yield self.focus_role
        yield self.nonpurge_role


class TrackingBlacklistData:
    __slots__ = ("guild", "blacklisted_channels", "blacklisted_users")

    def __init__(self, guild, blacklist):
        # blacklist is an iterable of (type, data_id)

        self.guild = guild
        blacklisted_channels, blacklisted_users = partition_on(
            lambda block: block[0] is LocationType.CHANNEL,
            blacklist,
            lambda block: block[1],
        )

        self.blacklisted_channels, self.blacklisted_users = (
            set(blacklisted_channels),
            set(blacklisted_users),
        )

    def is_blocked(self, user_or_channel):
        if isinstance(user_or_channel, discord.abc.User):
            return user_or_channel.id in self.blacklisted_users
        return user_or_channel.id in self.blacklisted_channels

    def add_block(self, user_or_channel):
        if isinstance(user_or_channel, discord.abc.User):
            self.blacklisted_users.add(user_or_channel.id)
        else:
            self.blacklisted_channels.add(user_or_channel.id)

    def remove_block(self, user_or_channel):
        if isinstance(user_or_channel, discord.abc.User):
            self.blacklisted_users.discard(user_or_channel.id)
        else:
            self.blacklisted_channels.discard(user_or_channel.id)
