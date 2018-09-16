#
# cogs/filter/download.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2018 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import asyncio
import logging
from io import BytesIO

import aiohttp

logger = logging.getLogger(__name__)

__all__ = [
    'MAXIMUM_FILE_SIZE',
    'download_attachments',
    'download_links',
]

# Maximum size to download from foreign sites
MAXIMUM_FILE_SIZE = 24 * 1024 * 1024

# How large each read request should be
CHUNK_SIZE = 4 * 1024

async def download_attachments(attachments):
    return await asyncio.gather(*[download_attachment(attach) for attach in attachments])

async def download_links(urls):
    async with aiohttp.ClientSession() as session:
        buffers = await asyncio.gather(*[download_link(session, url) for url in urls])
    return buffers

async def download_attachment(attachment):
    io = BytesIO()
    await attachment.save(io)
    return io

async def download_link(session, url):
    io = BytesIO()
    async with session.get(link) as response:
        while len(io.getbuffer()) < MAXIMUM_FILE_SIZE:
            chunk = await response.content.read(CHUNK_SIZE)
            if not chunk:
                break

            io.write(chunk)
    return io
