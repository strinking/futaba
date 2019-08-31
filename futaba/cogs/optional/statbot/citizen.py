#
# cogs/optional/statbot/citizen.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from collections import defaultdict

import discord
from discord.ext import commands

from futaba import permissions
from futaba.cogs.abc import AbstractCog
from futaba.converters import MemberConv
from futaba.exceptions import SendHelp

from futaba.journal.listener import Listener

guild_settings = {
    181866934353133570: {
        "tracked-channels": [
            # Collaborative
            300330466857189376,
            318429991794638848,
            # Topics
            483450551946838037,
            407344918466396172,
            217145262290894849,
            404339280748609546,
            361103290844446720,
            326026582823272458,
            211281315134308352,
            269597230292271104,
            412026066899566593,
            270653575905017856,
            181871712151928834,
            394264091209760789,
            205698752709787648,
            214921796015751169,
            200034977889517568,
            # Languages
            184740186436009984,
            182411915782389761,
            182411972409556992,
            182412379752103937,
            182411861386461184,
            346652222551097345,
            182412046518714368,
            579447665088004126,
        ],
        "first-class-role": 318430032861331476,
        "min-msg": 500,
    },
    247400063981191169: {
        "tracked-channels": [589312192902594576, 589312207301378048],
        "first-class-role": 589309608951021570,
        "min-msg": 50,
    },
}


class CitizenMessageListener(Listener):
    __slots__ = ("cog",)

    def __init__(self, router, bot, cog):
        super().__init__(router, "/tracking/message", recursive=True)
        self.cog = cog

    async def _handle(self, path, guild, _content, attributes):
        # pylint: disable=arguments-differ
        call = None
        if path.stem == "new":
            call = self.cog.handle_new
        elif path.stem == "delete":
            call = self.cog.handle_delete

        if call is not None:
            message = attributes["message"]
            await self.cog.freshen_cache(message)
            await call(guild, message)


class Citizen(AbstractCog):
    __slots__ = (
        "journal",
        "sql",
        "member_status_cache",
        "listening_from_message_id",
        "guild_settings",
    )

    def __init__(self, bot, sql):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/citizen")
        router = self.journal.router
        router.register(CitizenMessageListener(router, bot, self))

        self.member_status_cache = defaultdict(lambda: defaultdict(int))
        self.sql = sql

        self.listening_from_message_id = float("inf")
        self.guild_settings = None

    def setup(self):
        new_guild_settings = {}
        for guild_id, settings in guild_settings.items():
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue

            new_settings = {
                **settings,
                "first-class-role": guild.get_role(settings["first-class-role"]),
                "tracked-channels": [
                    guild.get_channel(id) for id in settings["tracked-channels"]
                ],
            }
            new_guild_settings[guild] = new_settings

        self.guild_settings = new_guild_settings

    async def freshen_cache(self, message):
        included_channels = []
        for guild in self.guild_settings:
            included_channels += [
                channel.id for channel in self.guild_settings[guild]["tracked-channels"]
            ]
        rollup = self.sql.rollup_channel_usage(
            before_message_id=message.id, included_channels=included_channels
        )

        for row in rollup:
            guild = self.bot.get_guild(row["guild_id"])
            member_id = row["real_user_id"]
            self.update_cache(guild, member_id, row["count"])

    async def update_cache(self, guild, member_id, points):
        self.member_status_cache[guild][member_id] += points
        return self.member_status_cache[guild][member_id]

    def is_channel_tracked(self, channel):
        return (channel.guild in self.guild_settings) and (
            channel in self.guild_settings[channel.guild]["tracked-channels"]
        )

    def is_member_already_citizen(self, guild, member):
        return self.guild_settings[guild]["first-class-role"] in member.roles

    async def handle_delete(self, guild, message):
        if not self.is_channel_tracked(message.channel):
            return
        await self.update_cache(guild, message.author.id, -1)

    async def handle_new(self, guild, message):
        if not self.is_channel_tracked(message.channel):
            return
        await self.update_cache(guild, message.author.id, 1)

    @commands.group(name="citizen", aliases=["citi", "civ"])
    @commands.guild_only()
    async def citizen(self, ctx):
        """
        Manages member citizenship based on message count.
        """
        if ctx.invoked_subcommand is None:
            raise SendHelp()

    async def check_channel(self, ctx):
        ok_channels = self.bot.sql.roles.get_role_command_channels(ctx.guild)

        # Any channel is allowed
        if not ok_channels:
            return

        # This channel is allowed
        if ctx.channel in ok_channels:
            return

        raise CommandFailed()

    @citizen.command(name="check", aliases=["c", "ch"])
    @commands.guild_only()
    async def check(self, ctx):
        """
        Reports a member's citizenship status.
        """

        await self.check_channel(ctx)

        settings = self.guild_settings[ctx.guild]
        messages, _, deleted = self.sql.message_count(
            ctx.guild, ctx.author, included_channels=settings["tracked-channels"]
        )
        existing_msgs = messages - deleted
        if existing_msgs >= settings["min-msg"]:
            description = f"{ctx.author.mention}, thank you for your contributions!"
        else:
            description = f"{ctx.author.mention}, you'll get there soon! Just keep being a good citizen!"

        embed = discord.Embed()
        embed.colour = discord.Colour.dark_teal()
        embed.description = description
        await ctx.send(embed=embed)

    @citizen.command(name="query", aliases=["q", "que"])
    @commands.guild_only()
    @permissions.check_mod()
    async def query(self, ctx, member: MemberConv = None):
        """
        Reports a member's citizenship status.
        Can only be used by moderators.
        """

        if member is None:
            member = ctx.author

        settings = self.guild_settings[ctx.guild]
        messages, _, deleted = self.sql.message_count(
            ctx.guild, member, included_channels=settings["tracked-channels"]
        )
        existing_msgs = messages - deleted
        messages = messages or 1
        deleted_pct = deleted / messages * 100

        needs_msgs = settings["min-msg"]
        if existing_msgs >= needs_msgs:
            status = f"**QUALIFIES** (has at least {needs_msgs}) messages"
        else:
            status = f"**INSUFFICIENT** (still needs {needs_msgs - existing_msgs} more messages)"

        embed = discord.Embed()
        embed.colour = discord.Colour.dark_teal()
        embed.description = (
            f"{member.mention} has {existing_msgs} messages ({deleted_pct:.2}% deleted)\n"
            f"Member {status}"
        )
        await ctx.send(embed=embed)
