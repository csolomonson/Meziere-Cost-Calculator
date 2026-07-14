#!/bin/sh
set -eu

users_file="${COST_APP_USERS_JSON_FILE:-/var/lib/cost-app-users/app_users.json}"
users_seed="${COST_APP_USERS_SEED_FILE:-/run/secrets/app_users_seed}"

if [ ! -s "$users_file" ]; then
  mkdir -p "$(dirname "$users_file")"
  cp "$users_seed" "$users_file"
  chmod 600 "$users_file"
fi

exec uvicorn api:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips="*"
