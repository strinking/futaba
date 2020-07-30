#
# cogs/filter/check/common.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

from collections import namedtuple

from futaba.enums import FilterType

__all__ = [
    "MASK_NICK",
    "JournalProperties",
    "journal_violation",
    "journal_name_violation",
]

# The nickname to apply to cover up an offensive username
MASK_NICK = "<name hidden>"

JournalProperties = namedtuple("JournalProperties", ("verb", "path", "icon"))

JOURNAL_PROPERTIES = {
    FilterType.FLAG: JournalProperties(verb="Flagged", path="flag", icon="flag"),
    FilterType.BLOCK: JournalProperties(verb="Blocked", path="block", icon="deleted"),
    FilterType.JAIL: JournalProperties(verb="Jailed for", path="jail", icon="jail"),
}


def journal_violation(journal, head, message, filter_type, filter_text, flagged):
    props = JOURNAL_PROPERTIES[filter_type]
    user = message.author
    channel = message.channel
    content = (
        f"{props.verb} message content, tripped by `{filter_text}`: "
        f"`{flagged}` by {user.mention} in {channel.mention}"
    )
    journal.send(
        f"{head}/{props.path}",
        message.guild,
        content,
        icon=props.icon,
        filter_type=filter_type,
        filter_text=filter_text,
        flagged=flagged,
    )
    journal.send(
        f"jump/{head}/{props.path}",
        message.guild,
        message.jump_url,
        icons="previous",
        filter_type=filter_type,
        filter_text=filter_text,
        flagged=flagged,
    )


def journal_name_violation(
    journal, member, name_type, filter_type, filter_text, flagged
):
    props = JOURNAL_PROPERTIES[filter_type]
    content = (
        f"{props.verb} {name_type.value}, tripped by `{filter_text}`: "
        f"`{flagged}` by {member.mention}"
    )
    journal.send(
        f"{name_type.value}/{props.path}", member.guild, content, icon=props.icon
    )
    journal.send(
        f"jump/{name_type.value}/{props.path}",
        member.guild,
        f"{member.mention} (`{member.id}`)",
        icons="previous",
        filter_type=filter_type,
        filter_text=filter_text,
        flagged=flagged,
    )
