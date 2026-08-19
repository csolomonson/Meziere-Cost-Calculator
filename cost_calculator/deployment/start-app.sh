#!/bin/sh
set -eu

/app/deployment/configure-container.sh

exec uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips="*"
