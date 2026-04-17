 #!/usr/bin/env python3

from remote_client import apiclient_v3
import sys, config 

if len(sys.argv) < 2:
    print("Syntax: {} <API endpoint> [arguments...]")
    sys.exit(255)

c = apiclient_v3(config.api_server, config.api_key)
if sys.argv[1] == "select":
    print(c.select("".join(sys.argv[2:])))
elif sys.argv[1] == "execute":
    print(c.execute(sys.argv[2:]))
else:
    print("Valid endpoints are: select, execute")
    sys.exit(255)

