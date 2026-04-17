#!/usr/bin/env python3

from async_remote_client import apiclient_v4
import sys, config, asyncio

all_rows = [[0, 'hello'], [1, 'goodbye'], [2, 'farewell']]

def check(m, a, b):
    sys.stdout.write(f"{m} check: ")
    if a != b:
        sys.stdout.write("[FAIL]\n")
        print(f"<{a}> != <{b}>")
        return False
    else:
        sys.stdout.write("[PASS]\n")
        return True
    
async def main():
    c = apiclient_v4(config.api_server, config.api_key)    
    check("Session establish", await c.establish(), True)

    check("Execute", await c.execute('listen x'), True)
    
    results = await c.select('select * from mt')
    check("Batched select", results, all_rows)

    out = []
    async for row in c.stream('select * from mt'):
        out.append(row)
    check("Streamed select", out, all_rows)
        
    check("Server-bound parameter",
          await c.select_stream('select * from mt where row = %s', [0]),
          [all_rows[0]])
    
    check("Local-bound parameter",
          await c.select_stream('select * from mt where row = %l', [1]),
          [all_rows[1]])

    check("Local-bound identifier",
          await c.select_stream('select * from %i where row = 2', ['mt']),
          [all_rows[2]])

#    async for row in c.monitor():
#        print(row)
        
    check("Session termination", await c.close(), True)



asyncio.run(main())


