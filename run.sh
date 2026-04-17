#!/usr/bin/env bash

source venv/bin/activate
gunicorn dbserver:aio --bind 127.0.0.1:31313 -w 1 -k aiohttp.GunicornWebWorker
