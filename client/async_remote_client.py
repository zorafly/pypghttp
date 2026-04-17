
#!/usr/bin/env python3

import sys, os, urllib, pickle, aiohttp, json, ssl, config, certifi, asyncio

def connector():
    ctx = None
    if config.usessl:
        ctx = ssl.create_default_context(cafile=certifi.where())
        if config.ssl_devmode:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
    return aiohttp.TCPConnector(ssl=ctx)

class objview(object):
    def __init__(self, d):
        self.__dict__ = d

class apiclient_v4():
    def __init__(self, server, key):
        self.server = server
        self.key = key
        self.sid = None
        self.url = f"{self.server}/v4"

    def make_request(self, action, query=None, params=None):
        return json.dumps({
            'key': self.key,
            'sid': self.sid,
            'action': action,
            'query': query,
            'params': params})        
        
    async def request_post(self, session, action, query=None, params=None):
        request = self.make_request(action, query, params)
        async with session.post(self.url, data = request) as response:
            if response.status == 200:
                text = await response.text()
                try:
                    return json.loads(text)
                except:
                    return None
            return None

    async def request_get(self, session, action, query=None, params=None):
        request = self.make_request(action, query, params)
        async with session.get(self.url, params = request) as response:
            if response.status == 200:
                text = await response.text()
                return json.loads(text)
            return None

    async def request(self, target, action, query=None, params=None):
        conn = connector()
        async with aiohttp.ClientSession(connector=conn) as session:
            return await target(session, action, query, params)

    async def request_stream(self, action, query=None, params=None):
        request = self.make_request(action, query, params)
        conn = connector()
        async with aiohttp.ClientSession(connector=conn) as session:
            async with session.post(self.url, data = request) as response:
                async for line in response.content.iter_chunks():
                    if not line:
                        continue
                    if not line[0]:
                        continue
                    line = line[0].strip().split(b':', 1)[1]
                    line = json.loads(line)
                    if line['status'] == 200:
                        return
                    yield line['content']

    async def establish(self):
        resp = await self.request(self.request_post, "open")
        if not resp:
            return False
        self.sid = resp['content']
        return True

    async def close(self):
        resp = await self.request(self.request_post, "close")
        if not resp:
            return False
        self.sid = None
        return True
    
    async def execute(self, query, params=None):
        resp = await self.request(self.request_post, "execute", query, params)
        if not resp:
            return False
        if resp['status'] != 200:
            return False
        return True

    # Results batched on the server, then returned all at once
    async def select(self, query, params=None):
        resp = await self.request(self.request_post, "select", query, params)
        if not resp:
            return None
        return resp['content']

    # Results streamed from the server, then yielded one row at a time
    async def stream(self, query, params=None):
        async for e in self.request_stream("stream", query, params):
            yield e

    # Results batched on the client, then returned all at once
    async def select_stream(self, query, params=None):
        results = []
        async for e in self.request_stream("stream", query, params):
            results.append(e)
        return results

    async def monitor(self):
        async for e in self.request_stream("monitor", None):
            yield e
