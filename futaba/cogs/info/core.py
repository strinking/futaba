#
# cogs/info/core.py
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
Informational commands that make finding and gathering data easier.
"""

import logging
import re
import sys
import unicodedata
from collections import Counter
from itertools import chain, islice

import discord
from discord.ext import commands

from futaba import __version__
from futaba.converters import (
    EmojiConv,
    GuildChannelConv,
    MessageConv,
    RoleConv,
    UserConv,
)
from futaba.exceptions import CommandFailed, ManualCheckFailure
from futaba.permissions import mod_perm
from futaba.similar import similar_users
from futaba.str_builder import StringBuilder
from futaba.utils import (
    GIT_HASH,
    escape_backticks,
    fancy_timedelta,
    lowerbool,
    plural,
    user_discrim,
)
from futaba.unicode import UNICODE_CATEGORY_NAME
from ..abc import AbstractCog

logger = logging.getLogger(__name__)

MAX_ROLES_SHOWN = 20

__all__ = ["Info"]


def get_unicode_url(emoji):
    name = "-".join(map(lambda c: f"{ord(c):x}", emoji))
    return (
        f"https://raw.githubusercontent.com/twitter/twemoji/gh-pages/72x72/{name}.png"
    )


class Info(AbstractCog):
    """Cog for informational commands."""

    def setup(self):
        pass

    @commands.command(
        name="about", aliases=["futaba", "aboutme", "bot", "botinfo", "uptime"]
    )
    async def about(self, ctx):
        """Prints information about the running bot."""

        pyver = sys.version_info
        python_emoji = self.bot.get_emoji(self.bot.config.python_emoji_id) or ""
        discord_py_emoji = self.bot.get_emoji(self.bot.config.discord_py_emoji_id) or ""

        embed = discord.Embed()
        embed.set_thumbnail(url=self.bot.user.avatar_url)
        embed.set_author(name=f"Futaba v{__version__} [{GIT_HASH}]")
        embed.add_field(name="Running for", value=fancy_timedelta(self.bot.uptime))
        embed.add_field(
            name="Created by",
            value="[Programming Discord](https://discord.gg/010z0Kw1A9ql5c1Qe)",
        )
        embed.add_field(name="Source code", value="https://github.com/strinking/futaba")
        embed.description = "\n".join(
            (
                f"{python_emoji} Powered by Python {pyver.major}.{pyver.minor}.{pyver.micro}",
                f"{discord_py_emoji} Using discord.py {discord.__version__}",
                f"\N{TIMER CLOCK} Latency: {self.bot.latency:.3} s",
            )
        )

        if ctx.guild is not None:
            embed.colour = ctx.guild.me.colour

        await ctx.send(embed=embed)

    @commands.command(name="emoji", aliases=["emojis"])
    async def emoji(self, ctx, *, name: str = None):
        """
        Fetches information about the given emojis.
        This supports both Discord and unicode emojis, and will check
        all guilds the bot is in.
        """

        if name is None:
            # If no argument, list all emojis in guild.
            await self.list_emojis(ctx)
            return

        conv = EmojiConv()
        try:
            emoji = await conv.convert(ctx, name)
        except commands.BadArgument:
            emoji = None

        if emoji is None:
            embed = discord.Embed(colour=discord.Colour.red())
            embed.set_author(name=name)
            embed.description = (
                "No emoji with this name found or not in the same guild."
            )
        elif isinstance(emoji, discord.Emoji):
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = str(emoji)
            embed.set_author(name=name)
            embed.set_thumbnail(url=emoji.url)
            embed.add_field(name="Name", value=f"`{emoji.name}`")
            embed.add_field(
                name="Guild", value=f"{emoji.guild.name} (`{emoji.guild.id}`)"
            )
            embed.add_field(name="ID", value=str(emoji.id))
            embed.add_field(name="Managed", value=lowerbool(emoji.managed))
            embed.timestamp = emoji.created_at
        elif isinstance(emoji, str):

            def category(ch):
                return UNICODE_CATEGORY_NAME[unicodedata.category(ch)]

            try:
                emoji_name = ", ".join(map(unicodedata.name, emoji))
            except ValueError:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.set_author(name=emoji)
                embed.description = f"Unable to retrieve unicode name for `{emoji}`"
                raise CommandFailed(embed=embed)

            embed = discord.Embed(colour=discord.Colour.dark_gold())
            embed.description = emoji
            embed.set_author(name=name)
            embed.set_thumbnail(url=get_unicode_url(emoji))
            embed.add_field(name="Name", value=emoji_name)
            embed.add_field(
                name="Codepoint", value=", ".join(map(lambda c: str(ord(c)), emoji))
            )
            embed.add_field(name="Category", value="; ".join(map(category, emoji)))
        else:
            raise ValueError(f"Unknown emoji object returned: {emoji!r}")

        await ctx.send(embed=embed)

    @commands.command(
        name="lemoji",
        aliases=["lemojis", "allemoji", "allemojis", "listemoji", "listemojis"],
    )
    @commands.guild_only()
    async def all_emojis(self, ctx, modifier: str = None):
        """
        Lists all emojis in the guild.
        Add 'all' to list from all guilds.
        """

        await self.list_emojis(ctx, modifier == "all")

    async def list_emojis(self, ctx, all_guilds=False):
        contents = []
        content = StringBuilder()

        if all_guilds:
            if not mod_perm(ctx):
                raise ManualCheckFailure(content="Only moderators can do this.")

            guild_emojis = (guild.emojis for guild in self.bot.guilds)
            emojis = chain(*guild_emojis)
        else:
            emojis = ctx.guild.emojis

        logger.info("Listing all emojis within the guild")
        for emoji in emojis:
            managed = "M" if emoji.managed else ""
            content.writeln(
                f"- [{emoji}]({emoji.url}) id: `{emoji.id}`, name: `{emoji.name}` {managed}"
            )

            if len(content) > 1900:
                # Too long, break into new embed
                contents.append(str(content))

                # Start content over
                content.clear()

        if content:
            contents.append(str(content))

        for i, content in enumerate(contents):
            embed = discord.Embed(
                description=content, colour=discord.Colour.dark_teal()
            )
            embed.set_footer(text=f"Page {i + 1}/{len(contents)}")

            if i == 0:
                if all_guilds:
                    embed.set_author(name="Emojis in all guilds")
                else:
                    embed.set_author(name=f"Emojis within {ctx.guild.name}")

            await ctx.send(embed=embed)

    async def get_user(self, ctx, name):
        if name is None:
            return ctx.author
        else:
            conv = UserConv()
            try:
                return await conv.convert(ctx, name)
            except commands.errors.BadArgument:
                name = escape_backticks(name)
                prefix = self.bot.prefix(ctx.guild)
                embed = discord.Embed(colour=discord.Colour.red())
                embed.description = f"No user found for `{name}`. Try `{prefix}ufind`."
                raise CommandFailed(embed=embed)

    @commands.command(name="avatar", aliases=["profilepic"])
    async def avatar(self, ctx, *, name: str = None):
        """
        Displays the given user's avatar and its URL.
        If no argument is passed, the caller is checked instead.
        """

        user = await self.get_user(ctx, name)
        logger.info("Displaying avatar on '%s' (%d)", user.name, user.id)

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.set_author(name=user_discrim(user))
        embed.set_image(url=user.avatar_url)
        await ctx.send(content=user.avatar_url, embed=embed)

    @commands.command(
        name="uinfo", aliases=["user", "userinfo", "member", "memberinfo"]
    )
    async def uinfo(self, ctx, *, name: str = None):
        """
        Fetch information about a user, whether they are in the guild or not.
        If no argument is passed, the caller is checked instead.
        """

        user = await self.get_user(ctx, name)
        usernames, nicknames = self.bot.sql.alias.get_alias_names(ctx.guild, user)

        logger.info("Running uinfo on '%s' (%d)", user.name, user.id)

        # Status
        content = StringBuilder()
        if getattr(user, "status", None):
            status = (
                "do not disturb" if user.status == discord.Status.dnd else user.status
            )
            content.writeln(f"{user.mention}, {status}")
        else:
            content.writeln(user.mention)

        embed = discord.Embed()
        embed.timestamp = user.created_at
        embed.set_author(name=user_discrim(user))
        embed.set_thumbnail(url=user.avatar_url)

        # User colour
        if hasattr(user, "colour"):
            embed.colour = user.colour

        embed.add_field(name="ID", value=f"`{user.id}`")
        self.uinfo_add_roles(embed, user)
        self.uinfo_add_activity(embed, user, content)

        embed.description = str(content)
        content.clear()

        self.uinfo_add_voice(embed, user)
        self.uinfo_add_aliases(embed, content, usernames, nicknames)

        # Guild join date
        if hasattr(user, "joined_at"):
            embed.add_field(name="Member for", value=fancy_timedelta(user.joined_at))

        # Discord join date
        embed.add_field(name="Account age", value=fancy_timedelta(user.created_at))

        # Send them
        await ctx.send(embed=embed)

    @staticmethod
    def uinfo_add_roles(embed, user):
        if getattr(user, "roles", None):
            roles_len = min(len(user.roles), MAX_ROLES_SHOWN + 1)
            roles = " ".join(role.mention for role in islice(user.roles, 1, roles_len))

            if len(user.roles) > roles_len:
                roles = f"{roles} (and {len(user.roles) - roles_len} others)"

            if roles:
                embed.add_field(name="Roles", value=roles)

    @staticmethod
    def uinfo_add_activity(embed, user, content):
        if getattr(user, "activity", None):
            act = user.activity
            if isinstance(act, discord.Game):
                if act.start is None:
                    if act.end is None:
                        time_msg = ""
                    else:
                        time_msg = f"until {act.end}"
                else:
                    if act.end is None:
                        time_msg = f"since {act.start}"
                    else:
                        time_msg = f"from {act.start} to {act.end}"

                content.writeln(f"Playing `{act.name}` {time_msg}")
            elif isinstance(act, discord.Streaming):
                content.writeln(f"Streaming [{act.name}]({act.url})")
                if act.details is not None:
                    content.writeln(f"\n{act.details}")
            elif isinstance(act, discord.Activity):
                content.writeln(f"{act.state} [{act.name}]({act.url})")

    @staticmethod
    def uinfo_add_voice(embed, user):
        if getattr(user, "voice", None):
            mute = user.voice.mute or user.voice.self_mute
            deaf = user.voice.deaf or user.voice.self_deaf

            states = StringBuilder(sep=" ")
            if mute:
                states.write("muted")
            if deaf:
                states.write("deafened")

            state = str(states) if states else "active"
            embed.add_field(name="Voice", value=state)

    @staticmethod
    def uinfo_add_aliases(embed, content, usernames, nicknames):
        if usernames:
            for username, timestamp in usernames:
                content.writeln(f"- `{username}` set {fancy_timedelta(timestamp)} ago")
            embed.add_field(name="Past usernames", value=str(content))
            content.clear()

        if nicknames:
            for nickname, timestamp in nicknames:
                content.writeln(f"- `{nickname}` set {fancy_timedelta(timestamp)} ago")
            embed.add_field(name="Past nicknames", value=str(content))
            content.clear()

    @commands.command(name="ufind", aliases=["userfind", "usearch", "usersearch"])
    async def ufind(self, ctx, *, name: str):
        """
        Perform a fuzzy search to find users who match the given name.
        They are listed with the closest matches first.
        Users not in this guild are marked with a \N{GLOBE WITH MERIDIANS}.
        """

        logger.info("Running ufind on '%s'", name)
        users = await similar_users(self.bot, name)
        users_not_in_guild = (
            set(member.id for member in ctx.guild.members) if ctx.guild else set()
        )
        descr = StringBuilder()

        for user in users:
            extra = "\N{GLOBE WITH MERIDIANS}" if user in users_not_in_guild else ""
            descr.writeln(f"- {user.mention} {user.name}#{user.discriminator} {extra}")

        if users:
            embed = discord.Embed(description=str(descr), colour=discord.Colour.teal())
        else:
            embed = discord.Embed(
                description="**No users found!**", colour=discord.Colour.red()
            )

        await ctx.send(embed=embed)

    @commands.command(name="rinfo", aliases=["roleinfo"])
    @commands.guild_only()
    async def rinfo(self, ctx, *, name: str = None):
        """
        Fetches and prints information about a particular role in the current guild.
        If no role is specified, it displays information about the default role.
        """

        if name is None:
            role = ctx.guild.default_role
        else:
            conv = RoleConv()
            try:
                role = await conv.convert(ctx, name)
            except commands.BadArgument:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.description = (
                    f"No role found in this guild for `{escape_backticks(name)}`."
                )
                raise CommandFailed(embed=embed)

        logger.info("Running rinfo on '%s' (%d)", role.name, role.id)

        embed = discord.Embed(colour=role.colour)
        embed.timestamp = role.created_at
        embed.add_field(name="ID", value=str(role.id))
        embed.add_field(name="Position", value=str(role.position))

        descr = StringBuilder(f"{role.mention}\n")
        if role.mentionable:
            descr.writeln("Mentionable")
        if role.hoist:
            descr.writeln("Hoisted")
        if role.managed:
            descr.writeln("Managed")
        embed.description = str(descr)

        if role.members:
            max_members = 10
            members = ", ".join(
                map(lambda m: m.mention, islice(role.members, 0, max_members))
            )
            if len(role.members) > max_members:
                diff = len(role.members) - max_members
                members += f" (and {diff} other{plural(diff)})"
        else:
            members = "(none)"

        embed.add_field(name="Members", value=members)

        await ctx.send(embed=embed)

    @commands.command(
        name="lrole", aliases=["lroles", "allrole", "allroles", "listrole", "listroles"]
    )
    @commands.guild_only()
    async def roles(self, ctx):
        """Lists all roles in the guild."""

        contents = []
        content = StringBuilder()

        logger.info("Listing roles within the guild")
        for role in ctx.guild.roles:
            content.writeln(
                f"- {role.mention} id: `{role.id}`, members: `{len(role.members)}`"
            )

            if len(content) > 1900:
                # Too long, break into new embed
                contents.append(str(content))

                # Start content over
                content.clear()

        if content:
            contents.append(str(content))

        for i, content in enumerate(contents):
            embed = discord.Embed(
                description=content, colour=discord.Colour.dark_teal()
            )
            embed.set_footer(text=f"Page {i + 1}/{len(contents)}")
            await ctx.send(embed=embed)

    @commands.command(name="message", aliases=["findmsg", "msg"])
    @commands.guild_only()
    async def message(self, ctx, *messages: MessageConv):
        """
        Finds and prints the contents of the messages with the given IDs.
        """

        logger.info("Displaying %d messages", len(messages))

        if not mod_perm(ctx) and len(messages) > 3:
            messages = islice(messages, 0, 3)
            await ctx.send(content="Too many messages requested, stopping at 3...")

        def make_embed(message):
            embed = discord.Embed(colour=message.author.colour)
            embed.description = message.content or None
            embed.timestamp = message.created_at
            embed.url = message.jump_url
            embed.set_author(
                name=f"{message.author.name}#{message.author.discriminator}"
            )
            embed.set_thumbnail(url=message.author.avatar_url)
            embed.add_field(name="Sent by", value=message.author.mention)

            if ctx.guild is not None:
                embed.add_field(name="Channel", value=message.channel.mention)

            embed.add_field(name="Permalink", value=message.jump_url)

            if message.edited_at is not None:
                delta = fancy_timedelta(message.edited_at - message.created_at)
                embed.add_field(
                    name="Edited at",
                    value=f"`{message.edited_at}` ({delta} afterwords)",
                )

            if message.attachments:
                embed.add_field(
                    name="Attachments",
                    value="\n".join(attach.url for attach in message.attachments),
                )

            if message.embeds:
                embed.add_field(name="Embeds", value=str(len(message.embeds)))

            if message.reactions:
                emojis = Counter()
                for reaction in message.reactions:
                    emojis[str(reaction.emoji)] += 1

                embed.add_field(
                    name="Reactions",
                    value="\n".join(
                        (f"{count}: {emoji}" for emoji, count in emojis.items())
                    ),
                )

            return embed

        for message in messages:
            await ctx.send(embed=make_embed(message))

    @commands.command(name="rawmessage", aliases=["raw", "rawmsg"])
    @commands.guild_only()
    async def raw(self, ctx, *, argument: str):
        """
        Finds and prints the raw contents of the messages with the given IDs.
        """

        messages = []
        parts = re.split(r"\s+", argument)
        if not parts:
            raise CommandFailed(content="No message references or text passed")

        for part in parts:
            try:
                message = await MessageConv().convert(ctx, part)
                messages.append(message)
            except Exception:
                await self.raw_argument(ctx, argument)
                return

        await self.raw_message(ctx, messages)

    async def raw_argument(self, ctx, argument):
        logger.info("Outputting raw form of the argument: '%s'", argument)

        content = "You sent:\n" f"```\n{escape_backticks(argument)}\n```"
        await ctx.send(content=content)

    async def raw_message(self, ctx, messages):
        logger.info("Outputting raw message contents for %d messages", len(messages))

        if not mod_perm(ctx) and len(messages) > 4:
            messages = islice(messages, 0, 4)
            await ctx.send(content="Too many messages requested, stopping at 5...")

        for message in messages:
            content = (
                f"{message.author.name}#{message.author.discriminator} sent:\n"
                f"```\n{escape_backticks(message.content)}\n```"
            )
            await ctx.send(content=content)

    @commands.command(name="embeds")
    @commands.guild_only()
    async def embeds(self, ctx, *, message: MessageConv):
        """
        Finds and copies embeds from the given message.
        """

        logger.info("Copying embeds from message ID %d", message.id)

        if not message.embeds:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = "This message contains no embeds."
            await ctx.send(embed=embed)
            return

        for i, embed in enumerate(message.embeds, 1):
            await ctx.send(content=f"#{i}:", embed=embed)

    @commands.command(name="reactions", aliases=["reacts"])
    @commands.guild_only()
    async def reactions(self, ctx, *, message: MessageConv):
        """
        Displays all reactions on a message.
        """

        logger.info("Displaying reactions for message ID %d", message.id)

        if not message.reactions:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = "This message has no reactions."
            await ctx.send(embed=embed)
            return

        descr = StringBuilder()
        for reaction in message.reactions:
            if descr:
                descr.writeln()

            descr.write(reaction.emoji)
            async for user in reaction.users():
                descr.write(f" {user.mention}")

                if len(descr) > 1800:
                    embed = discord.Embed(colour=discord.Colour.teal())
                    embed.description = str(descr)
                    await ctx.send(embed=embed)
                    descr.clear()
                    descr.write(reaction.emoji)

        if descr:
            embed = discord.Embed(colour=discord.Colour.teal())
            embed.description = str(descr)
            await ctx.send(embed=embed)

    @commands.command(name="cinfo", aliases=["chaninfo", "channelinfo"])
    @commands.guild_only()
    async def cinfo(self, ctx, name: str = None):
        """
        Fetches and prints information about a channel from the guild.
        If no channel is specified, it displays information about the current channel.
        """

        if name is None:
            channel = ctx.channel
        else:
            conv = GuildChannelConv()
            try:
                channel = await conv.convert(ctx, name)
            except commands.BadArgument:
                embed = discord.Embed(colour=discord.Colour.red())
                embed.description = (
                    f"No channel found in this guild for `{escape_backticks(name)}`"
                )
                raise CommandFailed(embed=embed)

        logger.info("Running cinfo on '%s' (%d)", channel.name, channel.id)
        embed = discord.Embed()
        embed.timestamp = channel.created_at
        embed.add_field(name="ID", value=str(channel.id))
        embed.add_field(name="Position", value=str(channel.position))
        channel_category_name = channel.category.name if channel.category else "(none)"

        if hasattr(channel, "is_nsfw"):
            nsfw = "\N{NO ONE UNDER EIGHTEEN SYMBOL}" if channel.is_nsfw() else ""

        if isinstance(channel, discord.TextChannel):
            embed.description = f"\N{MEMO} Text channel - {channel.mention} {nsfw}"
            embed.add_field(name="Topic", value=(channel.topic or "(no topic)"))
            embed.add_field(name="Channel category", value=channel_category_name)
            embed.add_field(name="Changed roles", value=str(len(channel.changed_roles)))
            embed.add_field(name="Members", value=str(len(channel.members)))
        elif isinstance(channel, discord.VoiceChannel):
            embed.description = (
                f"\N{STUDIO MICROPHONE} Voice channel - {channel.mention}"
            )
            embed.add_field(name="Channel category", value=channel_category_name)
            embed.add_field(name="Changed roles", value=str(len(channel.changed_roles)))
            embed.add_field(name="Bitrate", value=str(channel.bitrate))
            embed.add_field(name="User limit", value=str(channel.user_limit))
            embed.add_field(name="Members", value=str(len(channel.members)))
        elif isinstance(channel, discord.CategoryChannel):
            embed.description = (
                f"\N{BAR CHART} Channel category - {channel.name} {nsfw}"
            )
            chans = "\n".join(chan.mention for chan in channel.channels)
            embed.add_field(name="Channels", value=(chans or "(none)"))
            embed.add_field(name="Channel category", value=channel_category_name)
            embed.add_field(name="Changed roles", value=str(len(channel.changed_roles)))
        else:
            raise ValueError(f"Unknown guild channel: {channel!r}")

        await ctx.send(embed=embed)

    @commands.command(name="channels", aliases=["chans", "listchannels", "listchans"])
    @commands.guild_only()
    async def channels(self, ctx):
        """Lists all channels in the guild."""

        def category(chan):
            if chan.category is None:
                return ""
            else:
                return f"[{chan.category.name}]"

        if ctx.guild.text_channels:
            text_channels = "\n".join(
                f"{chan.mention} {category(chan)}" for chan in ctx.guild.text_channels
            )
        else:
            text_channels = "(none)"

        if ctx.guild.voice_channels:
            voice_channels = "\n".join(
                f"{chan.name} {category(chan)}" for chan in ctx.guild.voice_channels
            )
        else:
            voice_channels = "(none)"

        if ctx.guild.categories:
            channel_categories = "\n".join(
                f"{chan.name} {category(chan)}" for chan in ctx.guild.categories
            )
        else:
            channel_categories = "(none)"

        # Create a list of embeds if any are too long

        total_len = 0
        embeds = []
        embed = discord.Embed()

        total_len += len(text_channels)
        if total_len >= 900:
            embeds.append(embed)
            embed = discord.Embed()
            total_len = 0

        embed.add_field(name="\N{MEMO} Text channels", value=text_channels)

        total_len += len(voice_channels)
        if total_len >= 900:
            embeds.append(embed)
            embed = discord.Embed()
            total_len = 0

        embed.add_field(
            name="\N{STUDIO MICROPHONE} Voice channels", value=voice_channels
        )

        total_len += len(channel_categories)
        if total_len >= 900:
            embeds.append(embed)
            embed = discord.Embed()
            total_len = 0

        embed.add_field(
            name="\N{BAR CHART} Channel categories", value=channel_categories
        )

        embeds.append(embed)

        # Add all embeds

        for embed in embeds:
            await ctx.send(embed=embed)

    @commands.command(name="ginfo", aliases=["guildinfo"])
    @commands.guild_only()
    async def ginfo(self, ctx):
        """Gets information about the current guild."""

        embed = discord.Embed()
        embed.timestamp = ctx.guild.created_at
        embed.set_author(name=ctx.guild.name)
        embed.set_thumbnail(url=ctx.guild.icon_url)

        descr = StringBuilder()
        descr.writeln(f"\N{MAN} **Members:** {len(ctx.guild.members):,}")
        descr.writeln(f"\N{MILITARY MEDAL} **Roles:** {len(ctx.guild.roles):,}")
        descr.writeln(
            f"\N{BAR CHART} **Channel categories:** {len(ctx.guild.categories):,}"
        )
        descr.writeln(f"\N{MEMO} **Text Channels:** {len(ctx.guild.text_channels):,}")
        descr.writeln(
            f"\N{STUDIO MICROPHONE} **Voice Channels:** {len(ctx.guild.voice_channels):,}"
        )
        descr.writeln(
            f"\N{CLOCK FACE TWO OCLOCK} **Age:** {fancy_timedelta(ctx.guild.created_at)}"
        )
        descr.writeln()

        moderators = 0
        admins = 0
        bots = 0

        # Do a single loop instead of generator expressions
        for member in ctx.guild.members:
            if member.bot:
                bots += 1

            perms = member.permissions_in(ctx.channel)
            if perms.administrator:
                admins += 1
            elif perms.manage_messages:
                moderators += 1

        if bots:
            descr.writeln(f"\N{ROBOT FACE} **Bots:** {bots:,}")
        if moderators:
            descr.writeln(f"\N{CONSTRUCTION WORKER} **Moderators:** {moderators:,}")
        if admins:
            descr.writeln(f"\N{POLICE OFFICER} **Administrators:** {admins:,}")
        descr.writeln(f"\N{CROWN} **Owner:** {ctx.guild.owner.mention}")
        embed.description = str(descr)

        await ctx.send(embed=embed)
