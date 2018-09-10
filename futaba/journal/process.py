#
# journal/process.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

'''
Middleware for handling events before they are sent to all the listeners.
'''

__all__ = [
    'ICONS',
    'process_content',
]

ICONS = {
    # Logging levels
    'info': '\N{INFORMATION SOURCE}',
    'idea': '\N{ELECTRIC LIGHT BULB}',
    'warning': '\N{WARNING SIGN}',
    'error': '\N{CROSS MARK}',
    'forbidden': '\N{NO ENTRY}',
    'critical': '\N{SQUARED SOS}',
    'ok': '\N{SQUARED OK}',
    'announce': '\N{CHEERING MEGAPHONE}',

    # Moderation
    'ban': '\N{HAMMER}',
    'kick': '\N{WOMANS BOOTS}',
    'muffled': '\N{FACE WITH MEDICAL MASK}',
    'mute': '\N{SPEAK-NO-EVIL MONKEY}',
    'jail': '\N{POLICE CARS REVOLVING LIGHT}',

    # Filter
    'filter': '\N{PAGE WITH CURL}',
    'flag': '\N{TRIANGULAR FLAG ON POST}',
    'deleted': '\N{SKULL}',
    'nsfw': '\N{NO ONE UNDER EIGHTEEN SYMBOL}',

    # Mail
    'has-mail': '\N{OPEN MAILBOX WITH RAISED FLAG}',
    'no-mail': '\N{CLOSED MAILBOX WITH LOWERED FLAG}',

    # Watchdog
    'investigate': '\N{SLEUTH OR SPY}',
    'found': '\N{EYE}',

    # Configuration
    'edit': '\N{MEMO}',
    'save': '\N{FLOPPY DISK}',
    'writing': '\N{WRITING HAND}',
    'settings': '\N{HAMMER AND WRENCH}',

    # Development
    'deploy': '\N{ROCKET}',
    'package': '\N{PACKAGE}',
    'script': '\N{SCROLL}',

    # Security
    'key': '\N{KEY}',
    'lock': '\N{LOCK}',
    'unlock': '\N{OPEN LOCK}',

    # Documents
    'folder': '\N{OPEN FILE FOLDER}',
    'file': '\N{PAGE FACING UP}',
    'book': '\N{NOTEBOOK WITH DECORATIVE COVER}',
    'upload': '\N{OUTBOX TRAY}',
    'download': '\N{INBOX TRAY}',
    'bookmark': '\N{BOOKMARK}',
    'journal': '\N{LEDGER}',
    'attachment': '\N{PAPERCLIP}',
    'clipboard': '\N{CLIPBOARD}',
    'pin': '\N{PUSHPIN}',
    'briefcase': '\N{BRIEFCASE}',
    'cabinet': '\N{CARD FILE BOX}',
    'trash': '\N{WASTEBASKET}',

    # Miscellaneous
    'hourglass': '\N{HOURGLASS WITH FLOWING SAND}',
    'person': '\N{BUST IN SILHOUETTE}',
    'navigate': '\N{COMPASS}',
    'bot': '\N{ROBOT FACE}',
    'news': '\N{NEWSPAPER}',
    'art': '\N{ARTIST PALETTE}',
    'tag': '\N{TICKET}',
    'music': '\N{MUSICAL NOTE}',
    'link': '\N{LINK SYMBOL}',
    'alert': '\N{BELL}',
    'game': '\N{VIDEO GAME}',
    'search': '\N{LEFT-POINTING MAGNIFYING GLASS}',
    'bomb': '\N{BOMB}',
    'gift': '\N{WRAPPED PRESENT}',
    'celebration': '\N{PARTY POPPER}',
    'international': '\N{GLOBE WITH MERIDIANS}',
    'award': '\N{TROPHY}',
    'luck': '\N{FOUR LEAF CLOVER}',
}

def process_content(content, attributes):
    ''' Modifies the content based on the passed attributes. '''

    # Add icon
    icon = attributes.get('icon', None)
    if icon is not None:
        content = f'{ICONS[icon]} {content}'

    return content
