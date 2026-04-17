#!/usr/bin/env python

import aiohttp
from aiohttp import web
from aiohttp_wsgi import WSGIHandler
import core, os, hashlib, uuid, time, traceback, werkzeug, sys, subprocess, pickle, json, datetime, random, hashlib, asyncio, base64
from urllib.parse import urlparse
from msg_buffer import msg_buffer
from aiohttp_sse import sse_response

######## **** API endpoints **** ########
# Version 4 - Summer 2025               #
#######  *********************** ########

def make_reply(status, message, content):
    return json.dumps({
        'status': status,
        'message': message,
        'content': content
    })

def make_response(status, message, content, ctype='text/json'):
    reply = make_reply(status, message, content)
    return web.Response(status = status,
                        body = reply,
                        content_type = 'text/json',
                        charset = 'utf-8')

BUSY = lambda: make_response(503, "Busy", None)
INTERNAL_ERROR = lambda: make_response(500, "Internal Error", None)
FORBIDDEN = lambda: make_response(403, "Forbidden", None)
UNAUTHORIZED = lambda: make_response(401, "Unauthorized", None)
BAD_REQUEST = lambda: make_response(400, "Bad Request", None)
OK = lambda: make_response(200, "OK", None)
NEW_SESSION = lambda sid: make_response(200, "New Session", sid)

class TracebackCatcher():
    def __init__(self):
        self.buf = ""
    def write(self, msg):
        self.buf += msg

class Session():
    def __init__(self, db):
        self.sid = base64.b64encode(random.randbytes(24), b"-_").decode()
        self.atime = time.time()
        self.ctime = self.atime
        self.db = db

class Server():
    def __init__(self, **config):
        self.sessions = {}
        self.actions = {
            'verify': self.verify_v4,
            'open': self.open_v4,
            'close': self.close_v4,
            'execute': self.execute_v4,
            'select': self.select_v4,
            'stream': self.stream_v4,
            'monitor': self.monitor_v4
        }
        self.__dict__.update(config)
        
    async def terminate_session(self, sid):
        if sid not in self.sessions:
            return BAD_REQUEST()
        t = self.sessions[sid]
        del self.sessions[sid]
        await t.db.close()
        t.sid = None

    async def new_session(self):
        db = core.aconn(self.db_host, self.db_port, self.db_name,
                        self.db_user, self.db_pass, self.debug)
        await db.connect()
        session = Session(db)
        self.sessions[session.sid] = session
        return session

    async def verify_v4(self, request, session, query, params):
        return make_response(200, "OK", None)

    async def execute_v4(self, request, session, query, params):
        ret = await session.db.execute(query, params)
        if ret[0]:
            return OK()
        return INTERNAL_ERROR()

    async def select_v4(self, request, session, query, params):
        ret = await session.db.select(query, params)
        if ret[0]:
            results = await session.db.process_results(ret[1])
            return make_response(200, len(results), results)
        return INTERNAL_ERROR()

    async def stream_v4(self, request, session, query, params):
        ret = await session.db.select(query, params)
        if ret[0]:
            async with sse_response(request) as resp:
                i = 0
                async for record in ret[1]:
                    if not record:
                        continue
                    row = []
                    for item in record:
                        row.append(await session.db.convert_type(item))
                    await resp.send(make_reply(206, i, row))
                    i += 1
                await resp.send(make_reply(200, None, None))
                return resp
        return INTERNAL_ERROR()

    async def monitor_loop(self, request, session, resp):
        async for notif in session.db.dbconn.notifies():
            print(notif)
            await resp.send(make_reply(206, notif.channel, notif.payload))
        await resp.send(make_reply(200, None, None))
    
    async def monitor_v4(self, request, session, query, params):
        async with sse_response(request) as resp:
            try:
                await self.monitor_loop(request, session, resp)
            except:
                traceback.print_exc(file=sys.stderr)
                await resp.send(make_reply(500, "Internal Error", None))
            finally:
                return resp

    async def open_v4(self, request, session, query, params):
        if len(self.sessions) >= self.max_sessions:        
            return BUSY()
        s = await self.new_session()
        return NEW_SESSION(s.sid)

    async def close_v4(self, request, session, query, params):    
        await self.terminate_session(session.sid)
        return OK()

    async def remote_call_v4(self, request):
        try:
            if self.debug:
                catcher = TracebackCatcher()
            if request.method == "POST":
                data = await request.read()
                if self.debug:
                    print(f"<<<{data}")
                if data:
                    data = json.loads(data)
                else:
                    return OK()
            else:
                raise TypeError()            
            if type(data) != dict:
                return BAD_REQUEST()
            # Validate request
            if "action" not in data:
                return BAD_REQUEST()
            action = data["action"]
            if action not in self.actions:
                return BAD_REQUEST()
            if action == "open":
                session = None
                # Check API key 
                if "key" not in data:
                    return UNAUTHORIZED()
                if data["key"] != self.api_key:
                    return UNAUTHORIZED()
            else:
                # Check session key
                if "sid" not in data:
                    return FORBIDDEN()
                sid = data["sid"]
                if sid not in self.sessions:
                    return FORBIDDEN()
                session = self.sessions[sid]
                session.atime = time.time()
                query = None
                params = None
            if "query" in data:
                query = data["query"]
            if "params" in data:
                params = data["params"]
            return await self.actions[action](request, session, query, params)
        except:
            traceback.print_exc(file=catcher)
            sys.stderr.write(catcher.buf)
            sys.stderr.flush()
            if self.debug:
                return make_response(500, "Internal Error", catcher.buf)
            await terminate_session(session.sid)
            return make_response(500, "Internal Error", "Session terminated")
        return INTERNAL_ERROR()

    async def purge_expired(self):
        current = time.time()
        for s in self.sessions.copy().values():
            if current - s.atime >= SESSION_EXPIRE_TIME:
                await self.terminate_session(s.sid)

    async def sweeper(self):
        while 1:
            try:
                await asyncio.sleep(self.sweeper_interval)
                await self.purge_expired()
            except:
                traceback.print_exc(file=sys.stderr())
                return

    async def run(self):
        try:
            if self.web_ssl_cert:
                self.ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                if self.web_ssl_devmode:
                    self.ctx.check_hostname = False
                    self.ctx.verify_mode = ssl.CERT_NONE
                self.ctx.load_cert_chain(self.web_ssl_cert, self.web_ssl_key)
            else:
                self.ctx = None

            app = web.Application(client_max_size=self.rpc_max ** 2)
            app.add_routes(
                [web.get('/v4', self.remote_call_v4),
                 web.post('/v4', self.remote_call_v4)])
            self.runner = web.AppRunner(app)

            await self.runner.setup()

            self.site = aiohttp.web.TCPSite(self.runner,
                                            host=self.web_host,
                                            port=self.web_port,
                                            ssl_context=self.ctx)

            await self.site.start()

            asyncio.create_task(self.sweeper())
            print("Running")
        except:
            traceback.print_exc(file=sys.stderr)
        return False


    
def new_server(path):
    config = json.loads(open(path, mode="rb").read())
    return Server(**config)


async def main():
    s = new_server("config.json")
    await s.run()
    await asyncio.Event().wait()
    await s.runner.cleanup()
    
if __name__ == "__main__":
    asyncio.run(main())


