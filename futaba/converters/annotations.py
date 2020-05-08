#
# annotations.py
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
Module for managing the command annotations
"""

__all__ = ["ANNOTATIONS"]

ANNOTATIONS = {
    # Built-in
    "int": "Integer",
    "str": "String",
    "bool": "Boolean",
    # Discord.py
    "ClientUser": "Bot Client",
    "Relationship": "User Relationship",
    "User": "Discord User",
    "Attachment": "Message Attachment",
    "Message": "Discord Message",
    "Reaction": "Message Reaction",
    "CallMessage": "Group Call Message",
    "GroupCall": "Discord Group Call",
    "Guild": "Discord Guild/Server",
    "Member": "Guild/Server Member",
    "Spotify": "User's Spotify Activity",
    "VoiceState": "User's Voice State",
    "Emoji": "Discord Emoji",
    "PartialEmoji": "'Partial' Emoji",
    "Role": "Discord Role",
    "TextChannel": "Discord Text Channel",
    "VoiceChannel": "Discord Voice Channel",
    "CategoryChannel": "Discord Channel Category",
    "DMChannel": "Discord Direct Message Channel",
    "GroupChannel": "Discord Group Channel",
    "Invite": "Discord Invite",
    # futaba
    "TextChannelConv": "Discord Text Channel",
    "GuildChannelConv": "Discord Guild Channel",
    "EmojiConv": "Discord Emoji",
    "RoleConv": "Discord Role",
    "MemberConv": "Guild/Server Member",
    "UserConv": "Discord User",
}
