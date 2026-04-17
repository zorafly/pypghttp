#!/usr/bin/env python

query = 'bad \' stuff \\ {test} {escape me}'

import sanitize

print(sanitize.sanitize(query))
