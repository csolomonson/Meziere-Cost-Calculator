#!/usr/bin/env bash
set -Eeuo pipefail

state_root="${COST_APP_STATE_ROOT:-/var/lib/cost-calculator}"
config_file="$state_root/config/runtime.env"

load_runtime_config() {
    [[ -r "$config_file" ]] || {
        printf 'Runtime configuration is missing: %s\n' "$config_file" >&2
        printf 'Run this image with the configure command first.\n' >&2
        exit 1
    }

    local line key value
    while IFS= read -r line || [[ -n "$line" ]]; do
        [[ -n "$line" ]] || continue
        [[ "$line" == *=* ]] || {
            printf 'Ignoring malformed runtime setting: %s\n' "$line" >&2
            continue
        }
        key="${line%%=*}"
        value="${line#*=}"
        case "$key" in
            APP_HOSTNAME|APP_IP_ADDRESS|COST_DB_SERVER|COST_DB_USERNAME|COST_DB_DRIVER|COST_ERP_DATABASE|COST_APP_STORAGE_MODE|COST_APP_DATABASE|COST_APP_SCHEMA|COST_DB_TRUST_SERVER_CERTIFICATE|COST_DB_CONNECTION_TIMEOUT_SECONDS|COST_REPORT_COMPANY_NAME)
                if [[ -z "${!key+x}" ]]; then
                    printf -v "$key" '%s' "$value"
                    export "$key"
                fi
                ;;
            *)
                printf 'Ignoring unsupported runtime setting: %s\n' "$key" >&2
                ;;
        esac
    done < "$config_file"
}

command_name="${1:-serve}"
case "$command_name" in
    configure)
        shift
        exec /app/deployment/configure-image.sh configure "$@"
        ;;
    install-ca)
        shift
        exec /app/deployment/configure-image.sh install-ca "$@"
        ;;
    serve)
        load_runtime_config
        exec /app/deployment/start-app.sh
        ;;
    preflight)
        load_runtime_config
        /app/deployment/configure-container.sh
        exec python -m tools.deployment_preflight
        ;;
    database-setup)
        setup_file="$state_root/database/reset-selected-storage.sql"
        [[ -r "$setup_file" ]] || {
            printf 'Database setup has not been generated; run configure first.\n' >&2
            exit 1
        }
        exec cat "$setup_file"
        ;;
    export-ca)
        ca_file="$state_root/caddy/data/caddy/pki/authorities/local/root.crt"
        [[ -r "$ca_file" ]] || {
            printf 'Caddy has not generated its root certificate yet. Start the application first.\n' >&2
            exit 1
        }
        exec cat "$ca_file"
        ;;
    *)
        exec "$@"
        ;;
esac
