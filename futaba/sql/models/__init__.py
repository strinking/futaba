#
# sql/models/__init__.py
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
Module that contains models for interacting with SQL tables in a clean
and abstracted way.
"""

from .alias import AliasHistoryModel
from .filter import FilterModel
from .guilds import GuildsModel
from .journal import JournalModel
from .moderation import ModerationModel
from .navi import NaviModel
from .roles import RolesModel
from .settings import SettingsModel
from .welcome import WelcomeModel
