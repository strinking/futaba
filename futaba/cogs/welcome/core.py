#
# cogs/welcome/core.py
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
Cog for greeting new members, accepting !agree commands, and applying Member and Guest roles.
"""

import asyncio
import logging
import re
from collections import deque, namedtuple
from datetime import datetime, timedelta

import discord
from discord.ext import commands

from futaba import permissions
from futaba.exceptions import CommandFailed, InvalidCommandContext, SendHelp
from futaba.journal import ModerationListener
from futaba.utils import plural, user_discrim
from .role_reapplication import RoleReapplication
from ..abc import AbstractCog

# Can't use get_context() since there isn't a discord.Message to base it on.
FakeContext = namedtuple("FakeContext", ("author", "channel", "guild"))
logger = logging.getLogger(__name__)

__all__ = ["format_message", "Welcome"]

AGREE_REASON = "User agreed to the server's rules and policies"
AGREE_DELAY_MESSAGE = "Thank you for agreeing to the rules. Please wait while you are being transferred..."
FORMAT_HELP_LIST = """
If you want to send a literal `{` or `}`, send `{{` / `}}`.
Accepted parameters:
```
{mention}      - Text mentioning the user.
{user}         - The user's name. Does not include nicknames.
{discrim}      - The user's discriminator.
{user_discrim} - Username and discriminator, in the style of "user#1000".
{user_id}      - The user's discord ID.
{channel}      - Text mentioning the welcome channel.
{channel_name} - The name of the welcome channel. No "#" in front.
{channel_id}   - The welcome channel's discord ID.
{server}       - The server's name. Also aliased as {guild}.
{server_id}    - The server's discord ID. Also aliased as {guild_id}.
```
"""

MESSAGE_HIGHLIGHT_REGEX = re.compile(r"(\{[^\{\}]+\})")
message_highlight = (
    lambda s: "\n" + MESSAGE_HIGHLIGHT_REGEX.sub(r"`\1`", s) if s else "(none)"
)


def format_message(welcome_message, ctx):
    user = ctx.author
    channel = ctx.channel
    guild = ctx.guild

    return welcome_message.format(
        mention=user.mention,
        user=user.name,
        discrim=user.discriminator,
        user_discrim=user_discrim(user),
        user_id=user.id,
        channel=channel.mention,
        channel_name=channel.name,
        channel_id=channel.id,
        server=guild.name,
        server_id=guild.id,
        guild=guild.name,
        guild_id=guild.id,
    )


class Welcome(AbstractCog):
    __slots__ = ("journal", "roles", "recently_joined", "recently_saved_roles")

    def __init__(self, bot):
        super().__init__(bot)
        self.journal = bot.get_broadcaster("/welcome")
        self.roles = RoleReapplication(bot)
        self.recently_joined = deque(maxlen=5)
        self.recently_saved_roles = deque(maxlen=5)

        self.add_listener()
        bot.add_cog(self.roles)

    def setup(self):
        for guild in self.bot.guilds:
            self.bot.sql.welcome.get_welcome(guild)

    def add_listener(self):
        # Check if a moderation listener is already in place
        router = self.journal.router
        for listener in router.paths["/member/leave"]:
            if isinstance(listener, ModerationListener):
                return

        # If not, add listener
        router.register(ModerationListener(router, self.bot))

    @staticmethod
    def send_welcome_message(bot, member, fmt_message, channel):
        ctx = FakeContext(author=member, channel=channel, guild=member.guild)
        content = format_message(fmt_message, ctx)
        coro = channel.send(content=content)
        bot.queue.push(coro)

    @staticmethod
    async def check_welcome_message(ctx, fmt_message):
        response = None

        try:
            format_message(fmt_message, ctx)
        except ValueError as error:
            response = str(error)
        except KeyError as error:
            response = f"No such format parameter: {error}"
        except IndexError:
            response = "Invalid syntax"

        if response is not None:
            raise CommandFailed(content=response)

    async def member_join(self, member):
        logger.info(
            "Member %s (%d) joined '%s' (%d) %s",
            user_discrim(member),
            member.id,
            member.guild.name,
            member.guild.id,
            "(BOT)" if member.bot else "",
        )

        if member.bot:
            # Since bots have to be manually invited by an admin,
            # let them handle all the roles and stuff.
            return

        welcome = self.bot.sql.welcome.get_welcome(member.guild)
        roles = self.bot.sql.settings.get_special_roles(member.guild)

        # Delay to let Discord API catch up
        # Without this, some users won't receive the guest role
        await asyncio.sleep(2)

        if welcome.welcome_message and welcome.channel:
            self.send_welcome_message(
                self.bot, member, welcome.welcome_message, welcome.channel
            )

        if roles.guest:
            logger.info(
                "Adding role %s (%d) to new guest", roles.guest.name, roles.guest.id
            )
            await member.add_roles(roles.guest, reason="New user joined")

    async def member_update(self, before, after):
        for member, time in self.recently_saved_roles:
            if member == after:
                if datetime.now() - time < timedelta(microseconds=50000):
                    return

        self.recently_saved_roles.append((after, datetime.now()))
        await self.roles.member_update(before, after)

    async def member_leave(self, member):
        logger.info(
            "Member %s (%d) left '%s' (%d)",
            user_discrim(member),
            member.id,
            member.guild.name,
            member.guild.id,
        )

        welcome = self.bot.sql.welcome.get_welcome(member.guild)

        if welcome.goodbye_message and welcome.channel:
            self.send_welcome_message(
                self.bot, member, welcome.goodbye_message, welcome.channel
            )

        # Remove from recently_joined, they need to re-agree!
        try:
            self.recently_joined.remove(member)
        except ValueError:
            pass

    @commands.command(name="join", hidden=True)
    @commands.guild_only()
    async def join(self, ctx):
        """
        Command that absorbs bad attempts to join the server.
        Prevents people from copying those above them instead of reading the rules.
        """

        logger.debug("Command '!join' received, discarding")

        welcome = self.bot.sql.welcome.get_welcome(ctx.guild)

        if ctx.channel != welcome.channel:
            # Not the welcome channel, ignore
            raise InvalidCommandContext()

        if ctx.author.permissions_in(ctx.channel).manage_messages:
            # Not a guest, ignore
            raise InvalidCommandContext()

        if ctx.author in self.recently_joined:
            # Already joining, ignore
            raise InvalidCommandContext()

        await asyncio.gather(
            ctx.message.delete(), ctx.author.send("This is the wrong command!")
        )

    @commands.command(name="agree", aliases=["accept"], hidden=True)
    @commands.guild_only()
    async def agree(self, ctx):
        """
        Designate that you have agreed to the rules and other server information.
        Required to be able to access the server.
        """

        logger.debug("Unchecked !agree command received")

        welcome = self.bot.sql.welcome.get_welcome(ctx.guild)
        roles = self.bot.sql.settings.get_special_roles(ctx.guild)

        if ctx.channel != welcome.channel:
            # Not the welcome channel, ignore
            raise InvalidCommandContext()

        if ctx.author.permissions_in(ctx.channel).manage_messages:
            # Not a guest, ignore
            raise InvalidCommandContext()

        if ctx.author in self.recently_joined:
            # Already joining, ignore
            raise InvalidCommandContext()

        logger.info(
            "Guest %s (%d) just agreed to the rules and policies!",
            ctx.author.name,
            ctx.author.id,
        )

        self.recently_joined.append(ctx.author)
        temp_message = await ctx.send(content=AGREE_DELAY_MESSAGE)

        if welcome.delete_on_agree:
            await ctx.message.delete()

        # Delay adding roles to let Discord API catch up
        # Without this, some role changes might not be applied properly
        await asyncio.sleep(5)
        await temp_message.delete()

        if welcome.agreed_message:
            await ctx.send(content=format_message(welcome.agreed_message, ctx))

        # Reapply saved, old roles
        applied = await self.roles.reapply_roles(ctx.author)

        if roles.member and not applied:
            logger.info(
                "Adding member role %s (%d)", roles.member.name, roles.member.id
            )
            await ctx.author.add_roles(roles.member, reason=AGREE_REASON, atomic=True)

        if roles.guest:
            logger.info("Removing guest role %s (%d)", roles.guest.name, roles.guest.id)
            await ctx.author.remove_roles(roles.guest, reason=AGREE_REASON, atomic=True)

        # Send journal event
        agreer = f"{ctx.author.mention} ({user_discrim(ctx.author)})"
        content = f"User {agreer} has agreed to the rules and information"
        self.journal.send(
            "member/agree", ctx.guild, content, icon="agree", user=ctx.author
        )

        # Prevent the bot from attempting to add a success reaction
        if welcome.delete_on_agree:
            raise InvalidCommandContext()

    @commands.group(name="welcome", aliases=["wlm"])
    async def welcome(self, ctx):
        """Manages the welcome cog for managing new users and roles."""

        if ctx.invoked_subcommand is None:
            raise SendHelp()

    @welcome.command(name="getchan")
    @commands.guild_only()
    async def get_welcome_channel(self, ctx):
        """Gets the welcome channel."""

        welcome = self.bot.sql.welcome.get_welcome(ctx.guild)
        if welcome.channel:
            embed = discord.Embed(colour=discord.Colour.dark_teal())
            embed.description = f"Welcome channel set to {welcome.channel.mention}"
        else:
            embed = discord.Embed(colour=discord.Colour.dark_purple())
            embed.description = "No welcome channel set for this guild!"

        await ctx.send(embed=embed)

    @welcome.command(name="setchan")
    @commands.guild_only()
    @permissions.check_admin()
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        """Sets the welcome channel."""

        logger.info(
            "Setting welcome channel to #%s (%d) in guild '%s' (%d)",
            channel.name,
            channel.id,
            ctx.guild.name,
            ctx.guild.id,
        )

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_welcome_channel(ctx.guild, channel)

        content = (
            f"{user_discrim(ctx.author)} set the welcome channel to {channel.mention}"
        )
        self.journal.send(
            "channel/set",
            ctx.guild,
            content,
            icon="settings",
            channel=channel,
            cause=ctx.author,
        )

    @welcome.command(name="unsetchan")
    @commands.guild_only()
    @permissions.check_admin()
    async def unset_welcome_channel(self, ctx):
        """Unsets the welcome channel."""

        logger.info(
            "Unsetting the welcome channel in guild '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_welcome_channel(ctx.guild, None)

        content = f"{user_discrim(ctx.author)} unset the welcome channel"
        self.journal.send(
            "channel/set",
            ctx.guild,
            content,
            icon="settings",
            channel=None,
            cause=ctx.author,
        )

    @welcome.command(name="format")
    async def format(self, ctx):
        """Lists all parameters accepted when formatting welcome messages."""

        logger.info(
            "Sending list of accepted format parameters to %s (%d)",
            ctx.author.name,
            ctx.author.id,
        )

        try:
            await ctx.author.send(content=FORMAT_HELP_LIST)
        except discord.Forbidden:
            raise CommandFailed(content="I don't have permission to DM you")

    @welcome.command(name="getmsg")
    @commands.guild_only()
    async def get_messages(self, ctx):
        """Retrieves all configured welcome messages for this guild."""

        logger.info(
            "Sending list of all configured welcome messages for guild '%s' (%d)",
            ctx.guild.name,
            ctx.guild.id,
        )

        welcome = self.bot.sql.welcome.get_welcome(ctx.guild)
        welcome_message = message_highlight(welcome.welcome_message)
        goodbye_message = message_highlight(welcome.goodbye_message)
        agreed_message = message_highlight(welcome.agreed_message)

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        embed.description = "\n".join(
            (
                f"**Welcome message**: {welcome_message}",
                f"**Goodbye message**: {goodbye_message}",
                f"**Agree message**: {agreed_message}",
            )
        )

        await ctx.send(embed=embed)

    @welcome.command(name="welcomemsg")
    @commands.guild_only()
    @permissions.check_admin()
    async def set_welcome_message(self, ctx, *, welcome_message: str = None):
        """
        Sets the welcome message to newly joined users. No argument to unset.
        """

        logger.info(
            "Setting the welcome message in guild '%s' (%d): %r",
            ctx.guild.name,
            ctx.guild.id,
            welcome_message,
        )

        if welcome_message is not None:
            await self.check_welcome_message(ctx, welcome_message)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_welcome_message(ctx.guild, welcome_message or None)

        content = (
            f'{"Set" if welcome_message else "Unset"} new welcome message for the guild'
        )
        self.journal.send(
            "message/welcome",
            ctx.guild,
            content,
            icon="welcome",
            message=welcome_message,
        )

    @welcome.command(name="goodbyemsg")
    @commands.guild_only()
    @permissions.check_admin()
    async def set_goodbye_message(self, ctx, *, goodbye_message: str = None):
        """
        Sets the goodbye message for departing users. No argument to unset.
        """

        logger.info(
            "Setting the goodbye message in guild '%s' (%d): %r",
            ctx.guild.name,
            ctx.guild.id,
            goodbye_message,
        )

        if goodbye_message is not None:
            await self.check_welcome_message(ctx, goodbye_message)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_goodbye_message(ctx.guild, goodbye_message or None)

        content = (
            f'{"Set" if goodbye_message else "Unset"} new goodbye message for the guild'
        )
        self.journal.send(
            "message/goodbye",
            ctx.guild,
            content,
            icon="welcome",
            message=goodbye_message,
        )

    @welcome.command(name="agreemsg")
    @commands.guild_only()
    @permissions.check_admin()
    async def set_agreed_message(self, ctx, *, agreed_message: str = None):
        """
        Sets the message for users who have agreed to the rules. No argument to unset.
        """

        logger.info(
            "Setting the agree message in guild '%s' (%d): %r",
            ctx.guild.name,
            ctx.guild.id,
            agreed_message,
        )

        if agreed_message is not None:
            await self.check_welcome_message(ctx, agreed_message)

        with self.bot.sql.transaction():
            self.bot.sql.welcome.set_agreed_message(ctx.guild, agreed_message)

        content = (
            f'{"Set" if agreed_message else "Unset"} new agree message for the guild'
        )
        self.journal.send(
            "message/agree", ctx.guild, content, icon="welcome", message=agreed_message
        )

    @commands.command(name="guestify")
    @commands.guild_only()
    @permissions.check_mod()
    async def guestify(self, ctx):
        """
        In the event that the bot is not properly assigning guest roles to users,
        this command can be used to manually apply it to all roleless users.
        """

        roles = self.bot.sql.settings.get_special_roles(ctx.guild)
        if roles.guest is None:
            prefix = self.bot.prefix(ctx.guild)
            embed = discord.Embed(colour=discord.Colour.red())
            embed.description = (
                f"No guest role set.\nYou can assign one using `{prefix}guest <role>`."
            )
            raise CommandFailed(embed=embed)

        tasks = []
        for member in ctx.guild.members:
            if member.top_role == ctx.guild.default_role:
                tasks.append(
                    member.add_roles(
                        roles.guest, reason="Manually assigning guest role", atomic=True
                    )
                )
        await asyncio.gather(*tasks)

        embed = discord.Embed(colour=discord.Colour.dark_teal())
        if tasks:
            embed.description = f"Added the {roles.guest.mention} role to `{len(tasks)}` member{plural(len(tasks))}."
        else:
            embed.description = "No roleless members found."
        await ctx.send(embed=embed)
