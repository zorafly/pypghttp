#!/usr/bin/env python

def safe_char(c):
    if c < 20 or c > 126:
        return False
    if c == 34 or c == 39 or c == 123 or c == 125 or c == 92:
        return False
    return True

def sanitize(msg):
    unsafe = 0
    
    if type(msg) != type(bytes()):
        msg = bytes(msg, encoding='utf-8')
          
    for c in msg:
        if not safe_char(c):
            unsafe += 1

    size = len(msg) - unsafe
    buf = bytearray([0] * size)
    op = 0
    
    for c in msg:
        if safe_char(c):
            buf[op] = c
            op += 1

    return bytes(buf)
