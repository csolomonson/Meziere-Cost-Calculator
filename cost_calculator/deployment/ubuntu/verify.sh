#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
cd "$project_root"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    printf 'Run with sudo: sudo bash deployment/ubuntu/verify.sh\n' >&2
    exit 1
fi

docker compose config --quiet
docker compose ps
docker compose exec -T app python tools/deployment_preflight.py
app_hostname="$(sed -n 's/^APP_HOSTNAME=//p' .env | tail -n 1 | tr -d '\r')"
[[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != "localhost" ]]
curl --fail --silent --show-error --insecure --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/health" >/dev/null
curl --fail --silent --show-error --insecure --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/ready" >/dev/null

app_container="$(docker compose ps -q app)"
proxy_container="$(docker compose ps -q proxy)"
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$app_container")" == "healthy" ]]
[[ "$(docker inspect --format '{{.State.Running}}' "$proxy_container")" == "true" ]]

printf '\nAll automated deployment checks passed.\n'
printf 'Application image: %s\n' "$(docker inspect --format '{{.Config.Image}}' "$app_container")"
