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
import aiohttp
import json
import urllib.parse

#import requests

logger = logging.getLogger(__name__)

class gist(object):
    def __init__(self, oauth_token):
        
        self.github_api_url = "https://api.github.com/"
        self.github_gist_endpoint = urllib.parse.urljoin(self.github_api_url, "/gists")
        
        self.github_headers = {
                "Accept": "application/vnd.github.v3+json",
                "Authorization": f"token {oauth_token}"
        }

        self.session = aiohttp.ClientSession(headers=self.github_headers, raise_for_status=True)
    
    async def __del__(self):
        self.session.close()

    async def create_single(self, content, filename, description, public: bool):
        request_data = {
                "description": description,
                "public": public,
                "files": {
                    filename: {
                        "content": content
                    }
                }
        }

        async with self.session.post(self.github_gist_endpoint, json=request_data) as resp:
            #if resp.status == 201: # 201 Created status
            response_object = await resp.json() 
            return response_object.get("html_url")
            
            #else:
            #    logger.error("Failed to create gist and aiohttp did not throw. Status: %d.", resp.status)
            #    raise Exception()




