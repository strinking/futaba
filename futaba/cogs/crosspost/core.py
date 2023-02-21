"""
Cog for handling crosspost-style spam.
"""

import logging

from futaba.str_builder import StringBuilder
from ..abc import AbstractCog
from collections import OrderedDict
from discord import MessageType
from binascii import crc32

logger = logging.getLogger(__name__)

__all__ = ["Crosspost"]


class Crosspost(AbstractCog):
    __slots__ = ("history", "journal")

    def __init__(self, bot):
        super().__init__(bot)
        self.history = LRUDict(maxlen=126)
        bot.add_listener(self.check_message, "on_message")
        bot.add_listener(self.check_message_edit, "on_message_edit")
        self.journal = bot.get_broadcaster("/crosspost")

    def setup(self):
        pass

    async def check_message(self, message):
        # Don't filter PMs
        if message.guild is None:
            return

        # Don't check special messages
        if message.type != MessageType.default:
            return

        # Check that we actually have permissions to delete
        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        author_history = self.history.get(message.author.id)
        if author_history is None:
            author_history = LRUDict(maxlen=8)
            self.history[message.author.id] = author_history

        message_checksum = crc32(message.content.encode("utf-8"))
        message_posts = author_history.get(message_checksum)
        if message_posts is None:
            message_posts = {"messages": [], "channels": set()}
            author_history[message_checksum] = message_posts

        message_posts["channels"].add(message.channel.id)
        message_posts["messages"].append(message)

        if len(message_posts["channels"]) >= 5:
            await self.punish(message_posts["messages"])

    async def check_message_edit(self, _, after):
        await self.check_message(after)

    async def punish(self, messages):
        distinct_guild_messages = {msg.guild.id: msg for msg in messages}.values()
        for msg in distinct_guild_messages:
            roles = self.bot.sql.settings.get_special_roles(msg.guild)

            if roles.jail_role is None:
                logger.info(
                    "Jailing user for crosspost, except there is no jail role configured!"
                )
                content = f"Cannot jail {msg.author.mention} for crosspost violation because no jail role is set!"
                self.journal.send("member/jail", msg.guild, content, icon="warning")
            else:
                if not roles.jail_role in msg.author.roles:
                    response = f"The message you posted in {msg.channel.mention} has been reposted in multiple channels by you.\n"
                    response += f"As such, you have been asssigned the `{roles.jail_role.name}` role, until a moderator clears you."

                    await self.bot.punish.jail(
                        msg.guild, msg.author, "Jailed for crossposting"
                    )
                    await msg.author.send(content=response)

        for message in messages:
            await message.delete()
        messages.clear()


class LRUDict(OrderedDict):
    "Limit size, evicting the least recently looked-up key when full"

    def __init__(self, maxlen=128, *args, **kwds):
        self.maxlen = maxlen
        super().__init__(*args, **kwds)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if len(self) > self.maxlen:
            oldest = next(iter(self))
            del self[oldest]
