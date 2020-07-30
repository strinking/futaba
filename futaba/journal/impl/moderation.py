#
# journal/impl/moderation.py
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
A Listener for use by the moderation cog to properly output journal events for
kicks and ban events.
"""

import logging

from futaba.enums import MemberLeaveType
from futaba.utils import escape_backticks, user_discrim

from ..listener import Listener

logger = logging.getLogger(__name__)

__all__ = ["ModerationListener"]


class ModerationListener(Listener):
    def __init__(self, router, bot):
        super().__init__(router, "/member/leave", recursive=False)
        self.broadcaster = bot.get_broadcaster("/moderation")

    async def handle(self, _path, guild, _content, attributes):
        """
        Handle the incoming leave event, and output a kick or ban journal event as appropriate.
        """

        # We want to ignore two arguments
        # pylint: disable=arguments-differ

        leaver = attributes["member"]
        cause = attributes["cause"]

        logger.debug("Received member leave event: %s (%d)", leaver.name, leaver.id)

        if cause.type == MemberLeaveType.KICKED:
            action = "kicked"
            path = "member/kick"
            icon = "kick"
        elif cause.type == MemberLeaveType.BANNED:
            action = "banned"
            path = "member/ban"
            icon = "ban"
        else:
            # We don't care about this event!
            return

        # Get formatted reason
        if cause.reason:
            reason = f"with reason: `{escape_backticks(cause.reason)}`"
        else:
            reason = ""

        # Build journal event content
        mod = user_discrim(cause.cause)
        leaver_discrim = user_discrim(leaver)

        logger.info(
            "Sending journal event %s for %s (%d)", path, leaver.name, leaver.id
        )
        content = f"{mod} {action} {leaver.mention} ({leaver_discrim}) {reason}"
        self.broadcaster.send(path, guild, content, icon=icon)
