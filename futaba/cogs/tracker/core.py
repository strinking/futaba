#
# cogs/tracker/core.py
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
Cog for journaling live API events such as username changes, users joining and leaving, etc.
"""

import asyncio
import logging
from collections import deque, namedtuple
from datetime import datetime, timedelta

import discord
from discord import AuditLogAction

from futaba.enums import MemberLeaveType
from futaba.utils import user_discrim
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

__all__ = ["LISTENERS", "Tracker", "MessageDeletionReason", "MemberLeaveReason"]

MessageDeletionReason = namedtuple(
    "MessageDeletionReason",
    ("message", "cause", "count", "reason", "deleted_at", "audit_log_entry"),
)

MemberLeaveReason = namedtuple(
    "MemberLeaveReason",
    ("type", "member", "cause", "reason", "left_at", "audit_log_entry"),
)

LISTENERS = (
    "on_message",
    "on_message_edit",
    "on_message_delete",
    "on_bulk_message_delete",
    "on_reaction_add",
    "on_reaction_remove",
    "on_reaction_clear",
    "on_guild_channel_create",
    "on_guild_channel_delete",
    "on_member_join",
    "on_member_remove",
)


async def get_removal_cause(member, timestamp):
    async for entry in member.guild.audit_logs(limit=20):
        if abs(timestamp - entry.created_at) < timedelta(seconds=3):
            if entry.action == AuditLogAction.kick:
                if entry.target == member:
                    return MemberLeaveReason(
                        type=MemberLeaveType.KICKED,
                        member=member,
                        cause=entry.user,
                        reason=entry.reason,
                        left_at=entry.created_at,
                        audit_log_entry=entry,
                    )
            elif entry.action == AuditLogAction.ban:
                if entry.target == member:
                    return MemberLeaveReason(
                        type=MemberLeaveType.BANNED,
                        member=member,
                        cause=entry.user,
                        reason=entry.reason,
                        left_at=entry.created_at,
                        audit_log_entry=entry,
                    )
            elif entry.action == AuditLogAction.member_prune:
                # Unfortunately the audit log entry doesn't
                # tell us enough to determine if this member was part of
                # the prune, so we'll just take a leap of faith and say
                # it was so.

                return MemberLeaveReason(
                    type=MemberLeaveType.PRUNED,
                    member=member,
                    cause=entry.user,
                    reason=entry.reason,
                    left_at=entry.created_at,
                    audit_log_entry=entry,
                )

    # Couldn't find anything, must be a voluntary departure
    return MemberLeaveReason(
        type=MemberLeaveType.LEFT,
        member=member,
        cause=member,
        reason=None,
        left_at=timestamp,
        audit_log_entry=None,
    )


class Tracker(AbstractCog):
    __slots__ = (
        "journal",
        "new_messages",
        "edited_messages",
        "deleted_messages",
        "members_joined",
        "members_left",
        "reactions",
    )

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/tracking")
        self.new_messages = deque(maxlen=20)
        self.edited_messages = deque(maxlen=20)
        self.deleted_messages = deque(maxlen=20)
        self.members_joined = deque(maxlen=20)
        self.members_left = deque(maxlen=20)
        self.reactions = deque(maxlen=20)

    def setup(self):
        pass

    def cog_unload(self):
        """
        Remove listeners when unloading the cog.
        """

        for listener in LISTENERS:
            self.bot.remove_listener(getattr(self, listener), listener)

    @staticmethod
    def build_embed(message):
        embed = discord.Embed(description=message.content)
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.avatar_url
        )
        embed.timestamp = message.edited_at or message.created_at

        if message.attachments:
            embed.add_field(
                name="Attachments",
                value="\n".join(attach.url for attach in message.attachments),
            )
        if message.embeds:
            embed.add_field(name="Embeds", value=str(len(message.embeds)))

        return embed

    async def on_message(self, message):
        if message in self.new_messages:
            return
        else:
            self.new_messages.append(message)

        if message.guild is None or message.author == self.bot.user:
            return

        blacklist = self.bot.sql.settings.get_tracking_blacklist(message.guild)
        if blacklist.is_blocked(message.channel) or blacklist.is_blocked(
            message.author
        ):
            return

        logger.debug(
            "Received message from %s (%d) in #%s (%d)",
            message.author.name,
            message.author.id,
            message.channel.name,
            message.channel.id,
        )

        content = f"{user_discrim(message.author)} sent a message in {message.channel.mention}"
        self.journal.send(
            "message/new", message.guild, content, icon="message", message=message
        )
        self.journal.send(
            "jump/message/new",
            message.guild,
            message.jump_url,
            icon="previous",
            message=message,
        )
        self.journal.send(
            "full/message/new",
            message.guild,
            message.jump_url,
            icon="message",
            message=message,
            embed=self.build_embed(message),
        )

    async def on_message_edit(self, before, after):
        if after in self.edited_messages:
            return
        else:
            self.edited_messages.append(after)

        if after.guild is None or after.author == self.bot.user:
            return

        blacklist = self.bot.sql.settings.get_tracking_blacklist(after.guild)
        if blacklist.is_blocked(after.channel) or blacklist.is_blocked(after.author):
            return

        logger.debug(
            "Message %d by %s (%d) in #%s (%d) was edited",
            after.id,
            after.author.name,
            after.author.id,
            after.channel.name,
            after.channel.id,
        )

        content = f"{user_discrim(after.author)} edited message {after.id} in {after.channel.mention}"
        self.journal.send(
            "message/edit",
            after.guild,
            content,
            icon="edit",
            before=before,
            after=after,
        )
        self.journal.send(
            "jump/message/edit",
            after.guild,
            after.jump_url,
            icon="previous",
            before=before,
            after=after,
        )
        self.journal.send(
            "full/message/edit",
            after.guild,
            after.jump_url,
            icon="edit",
            before=before,
            after=after,
            embed=self.build_embed(after),
        )

    async def get_deletion_reason(self, message, timestamp):
        async for entry in message.guild.audit_logs(
            limit=20, action=AuditLogAction.message_delete
        ):
            if entry.after.id == message.id:
                if abs(timestamp - entry.created_at) < timedelta(seconds=3):
                    return MessageDeletionReason(
                        message=message,
                        cause=entry.user,
                        count=entry.extra.count,
                        reason=entry.reason,
                        deleted_at=timestamp,
                        audit_log_entry=entry,
                    )

        # Couldn't find anything, must be a self-delete.
        return MessageDeletionReason(
            message=message,
            cause=message.author,
            count=1,
            reason=None,
            deleted_at=timestamp,
            audit_log_entry=None,
        )

    async def on_message_delete(self, message):
        if message in self.deleted_messages:
            return
        else:
            self.deleted_messages.append(message)

        if message.guild is None:
            return

        blacklist = self.bot.sql.settings.get_tracking_blacklist(message.guild)
        if blacklist.is_blocked(message.channel) or blacklist.is_blocked(
            message.author
        ):
            return

        logger.debug(
            "Message %d by %s (%d) was deleted",
            message.id,
            message.author.name,
            message.author.id,
        )

        # Wait for a bit so we can catch the audit log entry
        timestamp = datetime.now()
        await asyncio.sleep(1)
        cause = await get_removal_cause(message, timestamp)

        content = f"Message {message.id} by {user_discrim(message.author)} was deleted"
        self.journal.send(
            "message/delete",
            message.guild,
            content,
            icon="delete",
            message=message,
            cause=cause,
        )
        self.journal.send(
            "jump/message/delete",
            message.guild,
            message.jump_url,
            icon="previous",
            message=message,
            cause=cause,
        )
        self.journal.send(
            "full/message/delete",
            message.guild,
            message.jump_url,
            icon="delete",
            message=message,
            embed=self.build_embed(message),
        )

    async def on_bulk_message_delete(self, messages):
        if not messages:
            return

        guild = messages[0].guild
        if guild is None:
            return

        channels = {message.channel for message in messages}
        logger.debug(
            "Bulk delete of %d messages across %d channels from guild '%s' (%d) performed",
            len(messages),
            len(channels),
            guild.name,
            guild.id,
        )

        content = f"{len(messages)} messages were bulk deleted"
        self.journal.send(
            "message/delete/bulk", guild, content, icon="delete", messages=messages
        )

        # Don't send full contents, with bulk deletes there could be a huge amount of messages

    async def on_reaction_add(self, reaction, user):
        if (reaction, user) in self.reactions:
            return
        else:
            self.reactions.append((reaction, user))

        message = reaction.message
        channel = message.channel
        emoji = reaction.emoji

        if message.guild is None or user == self.bot.user:
            return

        blacklist = self.bot.sql.settings.get_tracking_blacklist(message.guild)
        if blacklist.is_blocked(message.channel) or blacklist.is_blocked(user):
            logger.debug(
                "Ignoring reaction %s added to message %d by %s (%d) due to "
                "the channel or user adding the reaction being blacklisted",
                emoji,
                message.id,
                user.name,
                user.id,
            )
            return

        logger.debug(
            "Reaction %s added to message %d by %s (%d)",
            emoji,
            message.id,
            user.name,
            user.id,
        )
        content = (
            f"{user_discrim(user)} added reaction {emoji} to message "
            f"{message.id} in {channel.mention}"
        )
        self.journal.send(
            "reaction/add",
            message.guild,
            content,
            icon="item_add",
            reaction=reaction,
            user=user,
        )
        self.journal.send(
            "jump/reaction/add",
            message.guild,
            message.jump_url,
            icon="previous",
            message=message,
        )

    async def on_reaction_remove(self, reaction, user):
        message = reaction.message
        channel = message.channel
        emoji = reaction.emoji

        if message.guild is None or user == self.bot.user:
            return

        blacklist = self.bot.sql.settings.get_tracking_blacklist(message.guild)
        if blacklist.is_blocked(message.channel) or blacklist.is_blocked(user):
            logger.debug(
                "Ignoring reaction %s removed from message %d by %s (%d) due to "
                "the channel or user adding the reaction being blacklisted",
                emoji,
                message.id,
                user.name,
                user.id,
            )
            return

        logger.debug(
            "Reaction %s removed to message %d by %s (%d)",
            emoji,
            message.id,
            user.name,
            user.id,
        )
        content = f"{user_discrim(user)} removed reaction {emoji} from message {message.id} in {channel.mention}"
        self.journal.send(
            "reaction/remove",
            message.guild,
            content,
            icon="item_remove",
            reaction=reaction,
            user=user,
        )
        self.journal.send(
            "jump/reaction/remove",
            message.guild,
            message.jump_url,
            icon="previous",
            message=message,
        )

    async def on_reaction_clear(self, message, reactions):
        if message.guild is None:
            return

        blacklist = self.bot.sql.settings.get_tracking_blacklist(message.guild)
        if blacklist.is_blocked(message.channel):
            logger.debug(
                "Ignoring all reactions from message %d being removed due to the channel being blacklisted",
                message.id,
            )
            return

        logger.debug("All reactions from message %d were removed", message.id)
        content = f"All reactions on message {message.id} in {message.channel.mention} were removed"
        self.journal.send(
            "reaction/clear",
            message.guild,
            content,
            icon="item_clear",
            message=message,
            reactions=reactions,
        )
        self.journal.send(
            "jump/reaction/clear",
            message.guild,
            message.jump_url,
            icon="previous",
            message=message,
        )

    async def on_guild_channel_create(self, channel):
        logger.debug("Channel #%s (%d) was created", channel.name, channel.id)
        content = f"Guild channel {channel.mention} created"
        self.journal.send(
            "channel/new", channel.guild, content, icon="channel", channel=channel
        )

    async def on_guild_channel_delete(self, channel):
        logger.debug("Channel #%s (%d) was deleted", channel.name, channel.id)
        content = f"Guild channel #{channel.name} ({channel.id}) deleted"
        self.journal.send(
            "channel/delete", channel.guild, content, icon="delete", channel=channel
        )

    async def on_member_join(self, member):
        if member in self.members_joined:
            return
        else:
            self.members_joined.append(member)

        blacklist = self.bot.sql.settings.get_tracking_blacklist(member.guild)
        if blacklist.is_blocked(member):
            logger.debug(
                "Ignoring member %s (%d) joining guild '%s' (%d) due to the user being blacklisted",
                member.name,
                member.id,
                member.guild.name,
                member.guild.id,
            )
            return

        logger.debug(
            "Member %s (%d) joined '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        # For parity with on_member_remove(), so messages don't appear in incorrect order
        await asyncio.sleep(2)

        content = f"Member {member.mention} ({user_discrim(member)}) joined"
        self.journal.send(
            "member/join", member.guild, content, icon="join", member=member
        )

    async def on_member_remove(self, member):
        if member in self.members_left:
            return
        else:
            self.members_left.append(member)

        blacklist = self.bot.sql.settings.get_tracking_blacklist(member.guild)
        if blacklist.is_blocked(member):
            logger.debug(
                "Ignoring member %s (%d) leaving guild '%s' (%d) due to the user being blacklisted",
                member.name,
                member.id,
                member.guild.name,
                member.guild.id,
            )
            return

        logger.debug(
            "Member %s (%d) left '%s' (%d)",
            member.name,
            member.id,
            member.guild.name,
            member.guild.id,
        )

        # Wait for a bit so we can catch the audit log entry
        timestamp = datetime.now()
        await asyncio.sleep(2)
        cause = await get_removal_cause(member, timestamp)

        content = f"Member {member.mention} ({user_discrim(member)}) left"
        self.journal.send(
            "member/leave",
            member.guild,
            content,
            icon="leave",
            member=member,
            cause=cause,
        )
