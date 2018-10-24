#
# cogs/filter/check/common.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
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
MASK_NICK = "XXX"

JournalProperties = namedtuple("JournalProperties", ("verb", "path", "icon"))

JOURNAL_PROPERTIES = {
    FilterType.FLAG: JournalProperties(verb="Flagged", path="flag", icon="flag"),
    FilterType.BLOCK: JournalProperties(verb="Blocked", path="block", icon="deleted"),
    FilterType.JAIL: JournalProperties(verb="Jailed for", path="jail", icon="jail"),
}


def journal_violation(journal, head, message, filter_type, flagged):
    props = JOURNAL_PROPERTIES[filter_type]
    user = message.author
    channel = message.channel
    content = f"{props.verb} message content: `{flagged}` by {user.mention} in {channel.mention}"
    journal.send(f"{head}/{props.path}", message.guild, content, icon=props.icon)


def journal_name_violation(journal, member, name_type, filter_type, flagged):
    props = JOURNAL_PROPERTIES[filter_type]
    content = f"{props.verb} {name_type.value}: `{flagged}` by {member.mention}"
    journal.send(
        f"{name_type.value}/{props.path}", member.guild, content, icon=props.icon
    )
