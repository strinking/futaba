#
# sql/data/welcome.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import discord


class WelcomeData:
    __slots__ = (
        "guild",
        "welcome_message",
        "goodbye_message",
        "agreed_message",
        "delete_on_agree",
        "welcome_channel",
    )

    def __init__(
        self,
        guild,
        welcome_message=None,
        goodbye_message=None,
        agreed_message=None,
        delete_on_agree=True,
        welcome_channel_id=None,
    ):
        self.guild = guild
        self.welcome_message = welcome_message
        self.goodbye_message = goodbye_message
        self.agreed_message = agreed_message
        self.delete_on_agree = delete_on_agree
        self.welcome_channel = discord.utils.get(
            guild.text_channels, id=welcome_channel_id
        )

    @property
    def channel(self):
        return self.welcome_channel

    @property
    def channel_id(self):
        return self.welcome_channel_id

    @property
    def welcome_channel_id(self):
        return getattr(self.welcome_channel, "id", None)
