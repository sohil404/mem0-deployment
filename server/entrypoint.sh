#!/bin/sh
# Use a hardcoded port 8000
exec uvicorn main:app --host 0.0.0.0 --port 8000 