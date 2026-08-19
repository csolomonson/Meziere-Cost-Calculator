#!/bin/sh
set -eu

users_file="${COST_APP_USERS_JSON_FILE:-/var/lib/cost-app-users/app_users.json}"
users_seed="${COST_APP_USERS_SEED_FILE:-/run/secrets/app_users_seed}"
db_password_file="${COST_DB_PASSWORD_FILE:-/run/secrets/db_password}"

if [ ! -r "$db_password_file" ] || [ ! -s "$db_password_file" ]; then
  printf 'The SQL password secret is missing or unreadable: %s\n' "$db_password_file" >&2
  exit 1
fi

if [ ! -s "$users_file" ]; then
  if [ ! -r "$users_seed" ] || [ ! -s "$users_seed" ]; then
    printf 'The application-user seed is missing or unreadable: %s\n' "$users_seed" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$users_file")"
  cp "$users_seed" "$users_file"
  chmod 600 "$users_file"
fi

if [ ! -r "$users_file" ] || [ ! -s "$users_file" ]; then
  printf 'The persisted application-user file is missing or unreadable: %s\n' "$users_file" >&2
  exit 1
fi
