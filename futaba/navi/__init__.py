#
# cogs/navi/task/__init__.py
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
Module that has singular or recurring Navi task objects which will
be executed by Futaba in the future.
"""

from .abc import TASK_COMPLETE, AbstractNaviTask
from .change_roles import ChangeRolesTask, build_change_role_task
from .factory import build_navi_task
from .punish import PunishTask
from .send_message import SendMessageTask, build_send_message_task
