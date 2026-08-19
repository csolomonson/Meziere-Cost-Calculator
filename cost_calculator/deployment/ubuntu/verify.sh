#!/usr/bin/env bash
set -Eeuo pipefail

config_file="/etc/cost-calculator/runtime.env"
release_file="/etc/cost-calculator/release.env"
state_root="/var/lib/cost-calculator"
service_user="cost-calculator"
current_root="/opt/cost-calculator/current"
caddy_root="/var/lib/caddy/data/caddy/pki/authorities/local/root.crt"
exported_root="$state_root/caddy-root.crt"

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

[[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/verify.sh"
[[ -r "$config_file" && -r "$release_file" ]] || fail "The native VM configuration is incomplete."
[[ -x "$current_root/.venv/bin/python" ]] || fail "No application release is active."

systemctl is-active --quiet cost-calculator.service || {
    systemctl status --no-pager cost-calculator.service >&2 || true
    fail "cost-calculator.service is not active."
}
systemctl is-active --quiet caddy.service || {
    systemctl status --no-pager caddy.service >&2 || true
    fail "caddy.service is not active."
}

runuser -u "$service_user" -- bash -c '
    set -a
    source "$1"
    source "$2"
    set +a
    cd "$3"
    exec .venv/bin/python -m tools.deployment_preflight
' bash "$config_file" "$release_file" "$current_root"

set -a
# shellcheck disable=SC1090
source "$config_file"
# shellcheck disable=SC1090
source "$release_file"
set +a

[[ -s "$caddy_root" ]] || fail "Caddy has not generated its local root certificate."
install -m 0644 -o root -g root "$caddy_root" "$exported_root"
curl --fail --silent --show-error --cacert "$exported_root" \
    --resolve "$APP_HOSTNAME:443:127.0.0.1" "https://$APP_HOSTNAME/api/health" >/dev/null
curl --fail --silent --show-error --cacert "$exported_root" \
    --resolve "$APP_HOSTNAME:443:127.0.0.1" "https://$APP_HOSTNAME/api/ready" >/dev/null
curl --fail --silent --show-error --cacert "$exported_root" \
    "https://$APP_IP_ADDRESS/api/ready" >/dev/null

printf '\nAll automated native VM deployment checks passed.\n'
printf 'Application version: %s\n' "$APP_VERSION"
printf 'Application URL: https://%s/\n' "$APP_HOSTNAME"
printf 'Client trust certificate: %s\n' "$exported_root"
