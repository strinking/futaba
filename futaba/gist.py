#
# gist.py
#
# futaba - A Discord Mod bot for the Programming server
# Copyright (c) 2017-2020 Jake Richardson, Ammon Smith, jackylam5
#
# futaba is available free of charge under the terms of the MIT
# License. You are free to redistribute and/or modify it under those
# terms. It is distributed in the hopes that it will be useful, but
# WITHOUT ANY WARRANTY. See the LICENSE file for more details.
#

import logging
import json
import urllib.parse

import aiohttp

logger = logging.getLogger(__name__)

__all__ = ["create_single_gist"]
        
github_api_url = "https://api.github.com/"
github_gist_endpoint = urllib.parse.urljoin(github_api_url, "/gists")

async def create_single_gist(token, content, filename, description, public: bool):
 
    github_headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {token}"
    }
    request_data = {
            "description": description,
            "public": public,
            "files": {
                filename: {
                    "content": content
                }
            }
    }

    async with aiohttp.ClientSession(headers=github_headers, raise_for_status=True) as session:
        async with session.post(github_gist_endpoint, json=request_data) as resp:
            #if resp.status == 201: # 201 Created status
            response_object = await resp.json() 
            return response_object.get("html_url")
            




