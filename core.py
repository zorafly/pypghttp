#!/usr/bin/env python

import os, psycopg, uuid, traceback, datetime, sys
from psycopg import sql
from werkzeug.utils import secure_filename
from aiohttp_sse import sse_response

class aconn():
    def __init__(self, host, port, dbname, user, pwd, debug=False):
        self.connstring = f"host={host} port={port} dbname={dbname} "
        self.connstring += f"user={user} password={pwd}"
        self.debug = debug

    async def connect(self):
        self.dbconn = await psycopg.AsyncConnection.connect(self.connstring)
        self.dbcur = self.dbconn.cursor()
        
    async def close(self):
        await self.dbconn.close()

    async def convert_type(self, val):
        if type(val) == datetime.datetime:
            return float(time.mktime(val.timetuple()))
        elif type(val) == uuid.UUID:
            return str(val)
        elif type(val) == bytes:
            return val.decode(encoding='utf-8')
        else:
            return val

    async def process_results(self, cur):
        out = []
        async for record in cur:
            row = []
            for item in record:
                row.append(await self.convert_type(item))
            out.append(row)
        return tuple(out)

    async def form_query(self, query, params):
        if not params:
            return query, []
        p = query
        out = ""
        outparams = []
        e = 0
        s = 0
        i = 0
        while 1:
            if e > len(query):
                break
            p = p[e:]
            e = p.find("%")
            if e < 0:
                out += p
                break
            out += p[s:e]
            t = e + 1
            if t > len(query):
                break
            #Local bindings for identifiers, then literals
            if query[t] == "i":
                escaped = sql.Identifier(params[i]).as_string()
                out += escaped
                e += 2
            elif query[t] == "l":
                escaped = sql.Literal(params[i]).as_string()
                out += escaped
                e += 2
            #Placeholders for remote binding by the database server
            #You can only remote bind literals/values, not identifiers
            #See "Server-side binding" section of "Differences from psycopg2"
            #guide in the psycopg3 documentation for more details
            elif query[t] == "s":
                out += "%s"
                e += 2
                outparams.append(params[i])
            i += 1
            s = e
        if self.debug:
            print(f"\n\tquery formation:\n\t{out, outparams}\n")
        return out, outparams

    async def select(self, query, params):
        try:
            query, params = await self.form_query(query, params)
            ret = await self.dbcur.execute(query, params)
            return True, ret
        except:
            traceback.print_exc(file=sys.stderr)
            return False, None

    async def execute(self, query, params):
        try:
            query, params = await self.form_query(query, params)
            async with self.dbconn.transaction() as tx:
                try:
                    await self.dbcur.execute(query, params)
                    return True,
                except:
                    traceback.print_exc()
                    raise psycopg.Rollback()
        except:
            traceback.print_exc()
        return False,

