#!/bin/sh
set -eu

state_root="${COST_APP_STATE_ROOT:-/var/lib/cost-calculator}"
config_file="$state_root/config/runtime.env"
users_file="${COST_APP_USERS_JSON_FILE:-$state_root/users/app_users.json}"
db_password_file="${COST_DB_PASSWORD_FILE:-$state_root/secrets/db_password.txt}"
ca_bundle="${SSL_CERT_FILE:-$state_root/ca/ca-certificates.crt}"
base_ca_bundle="/usr/local/share/cost-calculator/ca-certificates.crt"
extra_ca="$state_root/ca/extra-ca.crt"

if [ ! -r "$base_ca_bundle" ] || [ ! -s "$base_ca_bundle" ]; then
  printf 'The image CA certificate bundle is missing: %s\n' "$base_ca_bundle" >&2
  exit 1
fi

temporary_ca="$(mktemp "$state_root/ca/ca-certificates.XXXXXX")"
cp "$base_ca_bundle" "$temporary_ca"
if [ -s "$extra_ca" ]; then
  printf '\n' >> "$temporary_ca"
  cat "$extra_ca" >> "$temporary_ca"
fi
chmod 0600 "$temporary_ca"
mv -f "$temporary_ca" "$ca_bundle"

for required_file in "$config_file" "$users_file" "$db_password_file" "$ca_bundle"; do
  if [ ! -r "$required_file" ] || [ ! -s "$required_file" ]; then
    printf 'Required runtime state is missing or unreadable: %s\n' "$required_file" >&2
    printf 'Run this image with the configure command before starting it.\n' >&2
    exit 1
  fi
done
