#
# dict_convert.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

""" Converts discord objects to JSON-safe dictionaries. """

import discord

from futaba.utils import map_or

__all__ = [
    "named_dict",
    "user_like_dict",
    "user_dict",
    "member_dict",
    "role_dict",
    "attachment_dict",
    "emoji_dict",
    "message_dict",
    "to_dict",
]


def named_dict(obj):
    return {"id": str(obj.id), "name": obj.name}


def user_like_dict(user):
    return {
        "id": str(user.id),
        "name": user.name,
        "nick": getattr(user, "nick", None),
        "discriminator": user.discriminator,
    }


def user_dict(user):
    return {
        "id": user.id,
        "name": user.name,
        "discriminator": user.discriminator,
        "avatar": str(user.avatar),
        "bot": user.bot,
    }


def member_dict(member):
    return {
        "id": member.id,
        "name": member.name,
        "discriminator": member.discriminator,
        "nick": member.nick,
        "avatar": str(member.avatar),
        "bot": member.bot,
        "joined_at": member.joined_at.isoformat(),
        "status": str(member.status),
    }


def role_dict(role):
    return {
        "id": role.id,
        "name": role.name,
        "permissions": role.permissions.value,
        "colour": role.colour.to_rgb(),
        "hoist": role.hoist,
        "position": role.position,
        "managed": role.managed,
        "mentionable": role.mentionable,
    }


def attachment_dict(attach):
    return {
        "id": str(attach.id),
        "size": attach.size,
        "height": attach.height,
        "width": attach.width,
        "filename": attach.filename,
        "url": attach.url,
        "proxy_url": attach.proxy_url,
    }


def emoji_dict(emoji):
    if isinstance(emoji, str):
        return emoji
    else:
        return {
            "id": str(emoji.id),
            "name": emoji.name,
            "animated": emoji.animated,
            "managed": getattr(emoji, "managed", False),
            "guild_id": map_or(str, getattr(emoji, "guild_id", None)),
            "url": str(emoji.url),
        }


def reaction_dict(react):
    return {
        "emoji": emoji_dict(react.emoji),
        "count": react.count,
        "message_id": str(react.message.id),
    }


def message_dict(message: discord.Message):
    return {
        "id": str(message.id),
        "tts": message.tts,
        "type": message.type.name,
        "author": user_dict(message.author),
        "content": message.content or message.system_content,
        "embeds": [embed.to_dict() for embed in message.embeds],
        "channel": named_dict(message.channel),
        "mention_everyone": message.mention_everyone,
        "user_mentions": [user_dict(user) for user in message.mentions],
        "channel_mentions": [named_dict(chan) for chan in message.channel_mentions],
        "role_mentions": [named_dict(role) for role in message.role_mentions],
        "pinned": message.pinned,
        "webhook_id": map_or(str, message.webhook_id),
        "attachments": [attachment_dict(attach) for attach in message.attachments],
        "reactions": [reaction_dict(react) for react in message.reactions],
        "activity": message.activity,
        "application": message.application,
        "guild_id": map_or(lambda g: str(g.id), message.guild),
        "edited_at": map_or(lambda d: d.isoformat(), message.edited_at),
    }


def to_dict(obj):
    if isinstance(obj, discord.User):
        return user_dict(obj)
    elif isinstance(obj, discord.Member):
        return member_dict(obj)
    elif isinstance(obj, discord.Role):
        return role_dict(obj)
    elif isinstance(obj, discord.Attachment):
        return attachment_dict(obj)
    elif isinstance(obj, (discord.Emoji, discord.PartialEmoji)):
        return emoji_dict(obj)
    elif isinstance(obj, discord.Message):
        return message_dict(obj)
    elif isinstance(obj, discord.Embed):
        return obj.to_dict()
    else:
        return obj
