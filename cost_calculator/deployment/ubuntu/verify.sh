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
docker compose exec -T app python -m tools.deployment_preflight
app_hostname="$(sed -n 's/^APP_HOSTNAME=//p' .env | tail -n 1 | tr -d '\r')"
app_ip_address="$(sed -n 's/^APP_IP_ADDRESS=//p' .env | tail -n 1 | tr -d '\r')"
ca_certificate="deployment/runtime/caddy-root.crt"
[[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != "localhost" ]]
[[ "$app_ip_address" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
[[ -s "$ca_certificate" ]]
curl --fail --silent --show-error --cacert "$ca_certificate" --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/health" >/dev/null
curl --fail --silent --show-error --cacert "$ca_certificate" --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/ready" >/dev/null
curl --fail --silent --show-error --cacert "$ca_certificate" "https://$app_ip_address/api/health" >/dev/null
curl --fail --silent --show-error --cacert "$ca_certificate" "https://$app_ip_address/api/ready" >/dev/null

app_container="$(docker compose ps -q app)"
proxy_container="$(docker compose ps -q proxy)"
[[ "$(docker inspect --format '{{.State.Health.Status}}' "$app_container")" == "healthy" ]]
[[ "$(docker inspect --format '{{.State.Running}}' "$proxy_container")" == "true" ]]

printf '\nAll automated deployment checks passed.\n'
printf 'Application image: %s\n' "$(docker inspect --format '{{.Config.Image}}' "$app_container")"
