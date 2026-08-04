#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
previous_image_file="$project_root/deployment/runtime/previous-image"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    printf 'Run with sudo: sudo bash deployment/ubuntu/rollback.sh\n' >&2
    exit 1
fi
[[ -s "$previous_image_file" ]] || {
    printf 'No previous application image was recorded; nothing was changed.\n' >&2
    exit 1
}

previous_image="$(tr -d '\r\n' < "$previous_image_file")"
[[ "$previous_image" == cost-calculator:* ]] || {
    printf 'Refusing unexpected rollback image: %s\n' "$previous_image" >&2
    exit 1
}

cd "$project_root"
printf 'Rolling the application back to %s. Docker volumes and databases will not be changed.\n' "$previous_image"
COST_APP_IMAGE="$previous_image" docker compose up -d --no-build --wait app proxy
app_hostname="$(sed -n 's/^APP_HOSTNAME=//p' .env | tail -n 1 | tr -d '\r')"
[[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != "localhost" ]]
curl --fail --silent --show-error --insecure --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/ready" >/dev/null
printf 'Rollback passed the readiness check. Run sudo bash deployment/ubuntu/verify.sh for the full check.\n'
