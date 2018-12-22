#
# cogs/filter/check/name.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2019 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
from collections import namedtuple

from futaba.enums import FilterType, InfractionType, NameType
from futaba.str_builder import StringBuilder
from futaba.utils import escape_backticks
from .common import MASK_NICK, journal_name_violation

logger = logging.getLogger(__name__)

__all__ = ["FoundNameViolation", "check_name_filter"]

FoundNameViolation = namedtuple("FoundNameViolation", ("filter_type", "filter_text"))


async def check_name_filter(cog, name, name_type, member):
    """
    Checks the given name against all filters, and enforces with a dunce.
    """

    logger.debug("Checking name: %r", name)

    # Iterate through all guild filters
    triggered = None

    for filter_text, (filter, filter_type) in cog.filters[member.guild].items():
        if filter.matches(name):
            if triggered is None or filter_type.value > triggered.filter_type.value:
                triggered = FoundNameViolation(
                    filter_type=filter_type, filter_text=filter_text
                )

    if triggered is None:
        logger.debug("No name violations found!")
        return

    filter_type = triggered.filter_type
    filter_text = triggered.filter_text
    escaped_name = escape_backticks(name)
    escaped_filter_text = escape_backticks(filter_text)

    logger.info(
        "Punishing name filter violation (%r, level %s) by '%s' (%d)",
        filter_text,
        filter_type.value,
        member.name,
        member.id,
    )

    roles = cog.bot.sql.settings.get_special_roles(member.guild)

    async def message_violator(jailed):
        response = StringBuilder(
            f"The {name_type.value} you just set violates a {filter_type.value} text filter "
            f"disallowing `{escaped_filter_text}`.\n"
        )

        if jailed:
            if roles.jail is not None:
                response.writeln(
                    f"In the mean time, you have been assigned the `{roles.jail.name}` role, "
                    "revoking your posting privileges until a moderator clears you."
                )
        else:
            response.writeln(
                "Your name has been manually cleared. Please do not set your name to "
                "anything offensive in the future."
            )

        await member.send(content=str(response))

    severity = filter_type.level
    jail_anyways = False

    if severity >= FilterType.FLAG.level:
        logger.info("Notifying staff of filter violation")
        journal_name_violation(
            cog.journal,
            member,
            name_type,
            filter_type,
            escaped_filter_text,
            escaped_name,
        )

        infr_type = InfractionType.from_filter_type(filter_type)
        cog.bot.sql.infraction.add_infraction(
            member,
            member,
            infr_type,
            {"name": name, "name_type": name_type.value, "filter_text": filter_text},
        )

    if severity >= FilterType.BLOCK.level:
        logger.info("Removing bad %s from member", name_type.value)
        if name_type == NameType.USER:
            jail_anyways = True
            await member.edit(
                nick=MASK_NICK,
                reason="Hid username for violating {filter_type.value} level name filter",
            )
        elif name_type == NameType.NICK:
            await member.edit(
                nick=None,
                reason=f"Removed nickname for violating {filter_type.value} level name filter",
            )
        else:
            raise ValueError(f"Unknown value for NameType: {name_type!r}")

    if severity >= FilterType.JAIL.level or jail_anyways:
        if roles.jail is None:
            logger.info(
                "Jailing user for inappropriate name, except there is no jail role configured!"
            )
            content = f"Cannot jail {member.mention} for name violation because no jail role is set!"
            cog.journal.send("name/jail", member.guild, content, icon="warning")
        else:
            logger.info("Jailing user for inappropriate name")
            await asyncio.gather(
                message_violator(jailed=True),
                cog.bot.punish.jail(
                    member.guild, member, "Jailed for violating name filter"
                ),
            )
