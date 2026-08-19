#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
runtime_dir="$project_root/deployment/runtime"
run_configuration=true
configuration_option=""

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    printf 'Usage: sudo bash deployment/ubuntu/start.sh [--configure-storage|--skip-configure]\n'
    printf 'The default runs startup configuration before starting the release containers.\n'
}

parse_args() {
    [[ "$#" -le 1 ]] || {
        usage >&2
        exit 2
    }
    case "${1:-}" in
        "") ;;
        --configure-storage) configuration_option="--configure-storage" ;;
        --skip-configure) run_configuration=false ;;
        --help|-h)
            usage
            exit 0
            ;;
        *) fail "Unknown startup option: $1" ;;
    esac
}

env_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$project_root/.env" | tail -n 1 | tr -d '\r'
}

on_error() {
    printf '\nStartup stopped on line %s. The previous image and Docker volumes were retained.\n' "$1" >&2
    if command -v docker >/dev/null 2>&1; then
        (cd "$project_root" && docker compose ps && docker compose logs --tail=80 app proxy) >&2 || true
    fi
}
trap 'on_error "$LINENO"' ERR

remember_previous_image() {
    local container_id previous_image new_image
    container_id="$(docker compose ps -q app 2>/dev/null || true)"
    [[ -n "$container_id" ]] || return 0
    previous_image="$(docker inspect --format '{{.Config.Image}}' "$container_id")"
    new_image="$(env_value COST_APP_IMAGE)"
    if [[ -n "$previous_image" && "$previous_image" != "$new_image" ]]; then
        printf '%s\n' "$previous_image" > "$runtime_dir/previous-image"
        chmod 0600 "$runtime_dir/previous-image"
    fi
}

export_caddy_root() {
    local attempt
    for attempt in {1..20}; do
        if docker compose cp proxy:/data/caddy/pki/authorities/local/root.crt "$runtime_dir/caddy-root.crt" >/dev/null 2>&1; then
            chmod 0644 "$runtime_dir/caddy-root.crt"
            return 0
        fi
        sleep 1
    done
    fail "Caddy did not create its local root certificate."
}

main() {
    parse_args "$@"
    [[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/start.sh"

    if [[ "$run_configuration" == "true" ]]; then
        if [[ -n "$configuration_option" ]]; then
            bash "$script_dir/configure.sh" "$configuration_option"
        else
            bash "$script_dir/configure.sh"
        fi
    fi

    [[ -f "$project_root/.env" ]] || fail ".env is missing; run startup without --skip-configure."
    [[ -s "$runtime_dir/ca-certificates.crt" ]] || fail "The runtime CA bundle is missing; run startup without --skip-configure."
    cd "$project_root"
    docker compose config --quiet
    remember_previous_image

    log "Starting the release containers and waiting for database-aware readiness"
    docker compose up -d --no-build --wait --remove-orphans
    export_caddy_root

    local app_hostname app_ip_address
    app_hostname="$(env_value APP_HOSTNAME)"
    app_ip_address="$(env_value APP_IP_ADDRESS)"
    curl --fail --silent --show-error --cacert "$runtime_dir/caddy-root.crt" --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/ready" >/dev/null
    curl --fail --silent --show-error --cacert "$runtime_dir/caddy-root.crt" "https://$app_ip_address/api/ready" >/dev/null

    log "Deployment succeeded"
    docker compose ps
    printf '\nApplication URLs:\n'
    printf '  Hostname: https://%s/\n' "$app_hostname"
    printf '  IPv4:    https://%s/\n' "$app_ip_address"
    printf 'Application image: %s\n' "$(env_value COST_APP_IMAGE)"
    printf 'Client trust certificate: %s\n' "$runtime_dir/caddy-root.crt"
    printf 'Verification command: sudo bash deployment/ubuntu/verify.sh\n'
    printf 'Rollback command: sudo bash deployment/ubuntu/rollback.sh\n'
}

main "$@"
