#
# download.py
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
    'download_links',
]

# Maximum size to download from foreign sites
MAXIMUM_FILE_SIZE = 24 * 1024 * 1024

# How large each read request should be
CHUNK_SIZE = 4 * 1024

async def download_links(urls):
    async with aiohttp.ClientSession() as session:
        buffers = await asyncio.gather(*[download_link(session, url) for url in urls])
    return buffers

async def download_link(session, url):
    binio = BytesIO()

    try:
        async with session.get(url) as response:
            while len(binio.getbuffer()) < MAXIMUM_FILE_SIZE:
                chunk = await response.content.read(CHUNK_SIZE)
                if not chunk:
                    return binio

                binio.write(chunk)
            logger.info("File was too large, bailing out (max file size: %d bytes)", MAXIMUM_FILE_SIZE)
            return None
    except Exception as error:
        logger.info("Error while downloading %s for hash check", url, exc_info=error)
        return None
