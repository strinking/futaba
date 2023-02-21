#
# sql/models/settings.py
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
Has the model for managing persistent bot settings.
"""

# False positive when using SQLAlchemy decorators
# pylint: disable=no-value-for-parameter

import functools
import logging

import discord

from sqlalchemy import and_
from sqlalchemy import (
    ARRAY,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Table,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.sql import select

from futaba.enums import LocationType
from futaba.utils import if_not_null
from ..data import (
    GuildSettingsData,
    ReapplyRolesData,
    SpecialRoleData,
    TrackingBlacklistData,
)
from ..hooks import register_hook

Column = functools.partial(Column, nullable=False)
logger = logging.getLogger(__name__)

__all__ = ["SettingsModel"]


class SettingsModel:
    __slots__ = (
        "sql",
        "tb_guild_settings",
        "tb_special_roles",
        "tb_reapply_roles",
        "tb_tracking_blacklists",
        "tb_optional_cog_settings",
        "guild_settings_cache",
        "special_roles_cache",
        "reapply_roles_cache",
        "tracking_blacklist_cache",
        "optional_cog_settings_cache",
    )

    def __init__(self, sql, meta):
        self.sql = sql
        self.tb_guild_settings = Table(
            "guild_settings",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("prefix", Unicode, nullable=True),
            Column("max_delete_messages", SmallInteger),
            Column("warn_manual_mod_action", Boolean),
            Column("remove_other_roles", Boolean),
            Column("mentionable_name_prefix", SmallInteger),
            CheckConstraint(
                "mentionable_name_prefix >= 0 AND mentionable_name_prefix <= 32",
                name="mentionable_name_prefix_in_range",
            ),
        )
        self.tb_special_roles = Table(
            "special_roles",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("member_role_id", BigInteger, nullable=True),
            Column("guest_role_id", BigInteger, nullable=True),
            Column("mute_role_id", BigInteger, nullable=True),
            Column("jail_role_id", BigInteger, nullable=True),
            Column("focus_role_id", BigInteger, nullable=True),
            Column("nonpurge_role_id", BigInteger, nullable=True),
            # Ensures special roles aren't assigned to @everyone
            CheckConstraint(
                "member_role_id is NULL OR member_role_id != guild_id",
                name="special_role_member_not_everyone_check",
            ),
            CheckConstraint(
                "guest_role_id is NULL or guest_role_id != guild_id",
                name="special_role_guest_not_everyone_check",
            ),
            CheckConstraint(
                "mute_role_id is NULL or mute_role_id != guild_id",
                name="special_role_mute_not_everyone_check",
            ),
            CheckConstraint(
                "jail_role_id is NULL or jail_role_id != guild_id",
                name="special_role_jail_not_everyone_check",
            ),
            CheckConstraint(
                "focus_role_id is NULL or focus_role_id != guild_id",
                name="special_role_focus_not_everyone_check",
            ),
            CheckConstraint(
                "nonpurge_role_id is NULL or nonpurge_role_id != guild_id",
                name="special_role_nonpurge_not_everyone_check",
            ),
            # Ensures Guest and punishment roles aren't the same as the Member role
            CheckConstraint(
                "guest_role_id is NULL OR guest_role_id != member_role_id",
                name="special_role_guest_not_member_check",
            ),
            CheckConstraint(
                "mute_role_id is NULL OR mute_role_id != member_role_id",
                name="special_role_mute_not_member_check",
            ),
            CheckConstraint(
                "jail_role_id is NULL OR jail_role_id != member_role_id",
                name="special_role_jail_not_member_check",
            ),
            CheckConstraint(
                "focus_role_id is NULL OR focus_role_id != member_role_id",
                name="special_role_focus_not_member_check",
            ),
            CheckConstraint(
                "nonpurge_role_id is NULL OR nonpurge_role_id != member_role_id",
                name="special_role_nonpurge_not_member_check",
            ),
        )
        self.tb_reapply_roles = Table(
            "reapply_roles",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("auto_reapply", Boolean),
            Column("role_ids", ARRAY(BigInteger)),
        )
        self.tb_tracking_blacklists = Table(
            "tracking_blacklists",
            meta,
            Column("guild_id", BigInteger, ForeignKey("guilds.guild_id"), index=True),
            Column("type", Enum(LocationType)),
            Column("data_id", BigInteger),
            UniqueConstraint(
                "guild_id", "type", "data_id", name="tracking_blacklist_uq"
            ),
            CheckConstraint(
                "type IN ('CHANNEL'::locationtype, 'USER'::locationtype)",
                name="type_is_channel_or_user_check",
            ),
        )
        self.tb_optional_cog_settings = Table(
            "optional_cog_settings",
            meta,
            Column(
                "guild_id", BigInteger, ForeignKey("guilds.guild_id"), primary_key=True
            ),
            Column("cog_name", String, primary_key=True),
            Column("settings", JSON),
        )

        self.guild_settings_cache = {}
        self.special_roles_cache = {}
        self.reapply_roles_cache = {}
        self.tracking_blacklist_cache = {}
        self.optional_cog_settings_cache = {}

        register_hook("on_guild_join", self.add_guild_settings)
        register_hook("on_guild_join", self.add_special_roles)
        register_hook("on_guild_join", self.add_reapply_roles)

    def add_guild_settings(self, guild):
        logger.info(
            "Adding guild settings row for new guild '%s' (%d)", guild.name, guild.id
        )
        ins = self.tb_guild_settings.insert().values(
            guild_id=guild.id,
            prefix=None,
            max_delete_messages=self.sql.max_delete_messages,
            warn_manual_mod_action=False,
            remove_other_roles=True,
            mentionable_name_prefix=0,
        )
        self.sql.execute(ins)
        self.guild_settings_cache[guild] = GuildSettingsData(
            None,
            self.sql.max_delete_messages,
            warn_manual_mod_action=False,
            remove_other_roles=True,
            mentionable_name_prefix=0,
        )

    def fetch_guild_settings(self, guild):
        logger.info("Getting guild settings for guild '%s' (%d)", guild.name, guild.id)

        sel = select(
            [
                self.tb_guild_settings.c.prefix,
                self.tb_guild_settings.c.max_delete_messages,
                self.tb_guild_settings.c.warn_manual_mod_action,
                self.tb_guild_settings.c.remove_other_roles,
                self.tb_guild_settings.c.mentionable_name_prefix,
            ]
        ).where(self.tb_guild_settings.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_guild_settings(guild)

        (
            prefix,
            max_delete_messages,
            warn_manual_mod_action,
            remove_other_roles,
            mentionable_name_prefix,
        ) = result.fetchone()
        self.guild_settings_cache[guild] = GuildSettingsData(
            prefix,
            max_delete_messages,
            warn_manual_mod_action=warn_manual_mod_action,
            remove_other_roles=remove_other_roles,
            mentionable_name_prefix=mentionable_name_prefix,
        )

    def ensure_guild_settings(self, guild):
        if guild not in self.guild_settings_cache:
            self.fetch_guild_settings(guild)

    def get_prefix(self, guild):
        self.ensure_guild_settings(guild)
        return self.guild_settings_cache[guild].prefix

    def set_prefix(self, guild, prefix):
        logger.info(
            "Setting prefix to %r for guild '%s' (%d)", prefix, guild.name, guild.id
        )
        self.ensure_guild_settings(guild)
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(prefix=prefix)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].prefix = prefix

    def get_max_delete_messages(self, guild):
        logger.info(
            "Getting maximum delete messages for guild '%s' (%d)", guild.name, guild.id
        )
        self.ensure_guild_settings(guild)
        return self.guild_settings_cache[guild].max_delete_messages

    def set_max_delete_messages(self, guild, max_delete_messages):
        logger.info(
            "Setting maximum delete messages to %d for guild '%s' (%d)",
            max_delete_messages,
            guild.name,
            guild.id,
        )
        self.ensure_guild_settings(guild)
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(max_delete_messages=max_delete_messages)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].max_delete_messages = max_delete_messages

    def get_warn_manual_mod_action(self, guild):
        logger.debug(
            "Getting warn manual mod action flag for guild '%s' (%d)",
            guild.name,
            guild.id,
        )
        self.ensure_guild_settings(guild)
        return self.guild_settings_cache[guild].warn_manual_mod_action

    def set_warn_manual_mod_action(self, guild, warn_manual_mod_action):
        logger.info(
            "Setting warn manual mod action flag to %s for guild '%s' (%d)",
            warn_manual_mod_action,
            guild.name,
            guild.id,
        )
        self.ensure_guild_settings(guild)
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(warn_manual_mod_action=warn_manual_mod_action)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].warn_manual_mod_action = warn_manual_mod_action

    def get_remove_other_roles(self, guild):
        self.ensure_guild_settings(guild)
        return self.guild_settings_cache[guild].remove_other_roles

    def set_remove_other_roles(self, guild, remove_other_roles):
        logger.info(
            "Setting whether to remove other roles on punishment to %s for guild '%s' (%d)",
            remove_other_roles,
            guild.name,
            guild.id,
        )
        self.ensure_guild_settings(guild)
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(remove_other_roles=remove_other_roles)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].remove_other_roles = remove_other_roles

    def get_mentionable_name_prefix(self, guild):
        self.ensure_guild_settings(guild)
        return self.guild_settings_cache[guild].mentionable_name_prefix

    def set_mentionable_name_prefix(self, guild, prefix):
        logger.debug(
            "Setting the mentionable name prefix for guild '%s' (%d) to %d",
            guild.name,
            guild.id,
            prefix,
        )
        self.ensure_guild_settings(guild)
        upd = (
            self.tb_guild_settings.update()
            .where(self.tb_guild_settings.c.guild_id == guild.id)
            .values(mentionable_name_prefix=prefix)
        )
        self.sql.execute(upd)
        self.guild_settings_cache[guild].mentionable_name_prefix = prefix

    def add_special_roles(self, guild):
        logger.info(
            "Adding special roles row for new guild '%s' (%d)", guild.name, guild.id
        )
        ins = self.tb_special_roles.insert().values(
            guild_id=guild.id,
            member_role_id=None,
            guest_role_id=None,
            mute_role_id=None,
            jail_role_id=None,
            focus_role_id=None,
            nonpurge_role_id=None,
        )
        self.sql.execute(ins)
        self.special_roles_cache[guild] = SpecialRoleData(guild, None, None, None, None)

    def get_special_roles(self, guild):
        if guild in self.special_roles_cache:
            return self.special_roles_cache[guild]

        sel = select(
            [
                self.tb_special_roles.c.member_role_id,
                self.tb_special_roles.c.guest_role_id,
                self.tb_special_roles.c.mute_role_id,
                self.tb_special_roles.c.jail_role_id,
                self.tb_special_roles.c.focus_role_id,
                self.tb_special_roles.c.nonpurge_role_id,
            ]
        ).where(self.tb_special_roles.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_special_roles(guild)
            return self.special_roles_cache[guild]

        (
            member_role_id,
            guest_role_id,
            mute_role_id,
            jail_role_id,
            focus_role_id,
            nonpurge_role_id,
        ) = result.fetchone()
        roles = SpecialRoleData(
            guild,
            member_role_id,
            guest_role_id,
            mute_role_id,
            jail_role_id,
            focus_role_id,
            nonpurge_role_id,
        )
        self.special_roles_cache[guild] = roles
        return roles

    def set_special_roles(self, guild, **attrs):
        logger.info("Setting special role(s) for guild '%s' (%d)", guild.name, guild.id)
        assert attrs, "No roles to change"

        values = {}
        for attr, role in attrs.items():
            assert attr in (
                "member",
                "guest",
                "mute",
                "jail",
                "focus",
                "nonpurge",
            ), "Unknown column"
            values[f"{attr}_role_id"] = getattr(role, "id", None)

        upd = (
            self.tb_special_roles.update()
            .where(self.tb_special_roles.c.guild_id == guild.id)
            .values(values)
        )
        self.sql.execute(upd)
        self.special_roles_cache[guild].update(attrs)

    def add_reapply_roles(self, guild):
        logger.info(
            "Adding reappliable roles row for new guild '%s' (%d)", guild.name, guild.id
        )
        ins = self.tb_reapply_roles.insert().values(
            guild_id=guild.id, auto_reapply=True, role_ids=[]
        )
        self.sql.execute(ins)
        self.reapply_roles_cache[guild] = ReapplyRolesData(set(), True)

    def fetch_reapply_roles(self, guild):
        logger.info(
            "Fetching reappliable roles for guild '%s' (%d)", guild.name, guild.id
        )
        sel = select(
            [self.tb_reapply_roles.c.auto_reapply, self.tb_reapply_roles.c.role_ids]
        ).where(self.tb_reapply_roles.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        if not result.rowcount:
            self.add_reapply_roles(guild)
            return self.reapply_roles_cache[guild]

        roles = set()
        auto_reapply, role_ids = result.fetchone()
        for role_id in role_ids:
            role = discord.utils.get(guild.roles, id=role_id)
            if role is not None:
                roles.add(role)

        storage = ReapplyRolesData(roles, auto_reapply)
        self.reapply_roles_cache[guild] = storage
        return storage

    def get_reapply_roles(self, guild):
        logger.info(
            "Getting reappliable roles for guild '%s' (%d)", guild.name, guild.id
        )
        if guild in self.reapply_roles_cache:
            return self.reapply_roles_cache[guild].roles
        else:
            return self.fetch_reapply_roles(guild).roles

    def update_reapply_roles(self, guild, roles, enable):
        logger.info(
            "Updating reappliable roles, %s %d roles for guild '%s' (%d)",
            "adding" if enable else "removing",
            len(roles),
            guild.name,
            guild.id,
        )

        old_roles = self.reapply_roles_cache[guild].roles
        if enable:
            new_roles = old_roles | roles
        else:
            new_roles = old_roles - roles

        if old_roles == new_roles:
            return

        upd = (
            self.tb_reapply_roles.update()
            .where(self.tb_reapply_roles.c.guild_id == guild.id)
            .values(role_ids=[role.id for role in new_roles])
        )

        self.sql.execute(upd)
        self.reapply_roles_cache[guild].roles = new_roles

    def get_auto_reapply(self, guild):
        logger.info(
            "Getting auto reapplication setting for guild '%s' (%d)",
            guild.name,
            guild.id,
        )
        if guild in self.reapply_roles_cache:
            return self.reapply_roles_cache[guild].auto_reapply
        else:
            return self.fetch_reapply_roles(guild).auto_reapply

    def set_auto_reapply(self, guild, auto_reapply):
        logger.info(
            "Setting automatic role reapplication to %s for guild '%s' (%d)",
            auto_reapply,
            guild.name,
            guild.id,
        )

        upd = (
            self.tb_reapply_roles.update()
            .where(self.tb_reapply_roles.c.guild_id == guild.id)
            .values(auto_reapply=auto_reapply)
        )
        self.sql.execute(upd)
        self.reapply_roles_cache[guild].auto_reapply = auto_reapply

    def add_to_tracking_blacklist(self, guild, user_or_channel):
        logger.info(
            "Adding '%s' (%d) to the tracking blacklist for guild '%s' (%d)",
            user_or_channel.name,
            user_or_channel.id,
            guild.name,
            guild.id,
        )

        block_type = (
            LocationType.USER
            if isinstance(user_or_channel, discord.abc.User)
            else LocationType.CHANNEL
        )

        ins = self.tb_tracking_blacklists.insert().values(
            guild_id=guild.id, type=block_type, data_id=user_or_channel.id
        )
        self.sql.execute(ins)
        if guild in self.tracking_blacklist_cache:
            self.tracking_blacklist_cache[guild].add_block(user_or_channel)

    def get_tracking_blacklist(self, guild):
        logger.debug(
            "Getting tracking blacklist for guild '%s' (%d)", guild.name, guild.id
        )
        if guild in self.tracking_blacklist_cache:
            return self.tracking_blacklist_cache[guild]

        sel = select(
            [self.tb_tracking_blacklists.c.type, self.tb_tracking_blacklists.c.data_id]
        ).where(self.tb_tracking_blacklists.c.guild_id == guild.id)
        result = self.sql.execute(sel)

        blacklist = TrackingBlacklistData(guild, result.fetchall())
        self.tracking_blacklist_cache[guild] = blacklist
        return blacklist

    def fetch_optional_cog_settings(self, guild, cog_name, default=None):
        logger.info(
            "Fetching or inserting settings for optional cog '%s' in guild '%s' (%d)",
            cog_name,
            guild.name,
            guild.id,
        )

        sel = select([self.tb_optional_cog_settings.c.settings]).where(
            and_(
                self.tb_optional_cog_settings.c.guild_id == guild.id,
                self.tb_optional_cog_settings.c.cog_name == cog_name,
            )
        )
        result = self.sql.execute(sel)

        if result.rowcount:
            (settings,) = result.fetchone()
        else:
            logger.info("Settings didn't exist, creating...")
            ins = self.tb_optional_cog_settings.insert().values(
                guild_id=guild.id, cog_name=cog_name, settings={}
            )
            self.sql.execute(ins)
            settings = if_not_null(default, {})

        self.optional_cog_settings_cache[(guild, cog_name)] = settings
        return settings

    def get_optional_cog_settings(self, guild, cog_name, default=None):
        logger.debug(
            "Getting settings for optional cog '%s' in guild '%s' (%d)",
            cog_name,
            guild.name,
            guild.id,
        )

        if (guild, cog_name) not in self.optional_cog_settings_cache:
            self.fetch_optional_cog_settings(guild, cog_name)

        return self.optional_cog_settings_cache[(guild, cog_name)]

    def set_optional_cog_settings(self, guild, cog_name, settings):
        logger.debug(
            "Updating settings for optional cog '%s' in guild '%s' (%d)",
            cog_name,
            guild.name,
            guild.id,
        )

        # Insert if it doesn't already exist
        _ = self.get_optional_cog_settings(guild, cog_name)

        upd = (
            self.tb_optional_cog_settings.update()
            .values(settings=settings)
            .where(
                and_(
                    self.tb_optional_cog_settings.c.guild_id == guild.id,
                    self.tb_optional_cog_settings.c.cog_name == cog_name,
                )
            )
        )
        self.sql.execute(upd)

        self.optional_cog_settings_cache[(guild, cog_name)] = settings
