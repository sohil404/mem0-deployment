#!/bin/sh
# Use default port 8000 if PORT is not set
PORT=${PORT:-8000}
exec uvicorn main:app --host 0.0.0.0 --port $PORT 