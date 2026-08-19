#!/usr/bin/env bash
set -Eeuo pipefail

config_dir="${COST_APP_CONFIG_DIR:-/etc/cost-calculator}"
state_root="${COST_APP_STATE_ROOT:-/var/lib/cost-calculator}"
config_file="$config_dir/runtime.env"
caddy_config_file="$config_dir/caddy.env"
users_file="$state_root/users/app_users.json"
db_password_file="$state_root/secrets/db_password.txt"
database_setup_file="$state_root/database/reset-selected-storage.sql"
service_user="${COST_APP_SERVICE_USER:-cost-calculator}"
service_group="${COST_APP_SERVICE_GROUP:-cost-calculator}"
source_root="${COST_APP_SOURCE_ROOT:-/opt/cost-calculator/current}"
app_python="${COST_APP_PYTHON:-$source_root/.venv/bin/python}"
reconfigure=false
replace_db_password=false

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    printf 'Usage: sudo bash deployment/ubuntu/configure.sh [--reconfigure] [--replace-db-password]\n'
    printf 'Creates missing native VM configuration and secrets.\n'
}

for option in "$@"; do
    case "$option" in
        --reconfigure) reconfigure=true ;;
        --replace-db-password) replace_db_password=true ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done
[[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/configure.sh"
id "$service_user" >/dev/null 2>&1 || fail "The $service_user service account is missing; run install.sh first."
[[ -x "$app_python" ]] || fail "The application environment is missing: $app_python"
[[ -r "$source_root/database/reset_schema.sql" ]] || fail "The application source is incomplete: $source_root"

install -d -m 0750 -o root -g "$service_group" "$config_dir"
install -d -m 0750 -o "$service_user" -g "$service_group" \
    "$state_root" "$state_root/users" "$state_root/update"
install -d -m 0750 -o root -g "$service_group" \
    "$state_root/secrets" "$state_root/database"

load_existing_config() {
    [[ -r "$config_file" ]] || return 0
    # This root-owned file is generated below using shell-safe values and is also
    # consumed by systemd's EnvironmentFile parser.
    set -a
    # shellcheck disable=SC1090
    source "$config_file"
    set +a
}

read_setting() {
    local prompt="$1"
    local default_value="$2"
    local result
    read -r -p "$prompt [$default_value]: " result
    printf '%s' "${result:-$default_value}"
}

is_ipv4() {
    local address="$1"
    local octet
    local -a octets
    IFS='.' read -r -a octets <<< "$address"
    [[ "${#octets[@]}" -eq 4 ]] || return 1
    for octet in "${octets[@]}"; do
        [[ "$octet" =~ ^[0-9]{1,3}$ ]] || return 1
        ((10#$octet <= 255)) || return 1
    done
    [[ "$address" != "0.0.0.0" && "$address" != "255.255.255.255" && "$address" != 127.* ]]
}

detect_primary_ipv4() {
    local candidate
    candidate="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{ for (i = 1; i <= NF; i++) if ($i == "src") { print $(i + 1); exit } }')" || candidate=""
    if is_ipv4 "$candidate"; then
        printf '%s' "$candidate"
        return
    fi
    for candidate in $(hostname -I 2>/dev/null); do
        if is_ipv4 "$candidate"; then
            printf '%s' "$candidate"
            return
        fi
    done
    return 1
}

validate_identifier() {
    [[ "$1" =~ ^[A-Za-z_][A-Za-z0-9_@\$-]{0,127}$ ]] || fail "Unsupported SQL identifier: $1"
}

validate_config_value() {
    [[ "$1" != *$'\n'* && "$1" != *$'\r'* && "$1" != *'#'* ]] || \
        fail "Configuration values cannot contain line breaks or #."
}

write_environment_value() {
    local name="$1"
    local value="$2"
    printf '%s=' "$name"
    printf '%q\n' "$value"
}

write_runtime_config() {
    load_existing_config
    local ip_default storage_choice trust_answer
    ip_default="${APP_IP_ADDRESS:-}"
    [[ -n "$ip_default" ]] || ip_default="$(detect_primary_ipv4)" || fail "Could not detect the VM IPv4 address."

    APP_HOSTNAME="$(read_setting "Application DNS hostname" "${APP_HOSTNAME:-cost-calculator.local}")"
    [[ "$APP_HOSTNAME" =~ ^[A-Za-z0-9.-]+$ && "$APP_HOSTNAME" != "localhost" && "$APP_HOSTNAME" != .* && "$APP_HOSTNAME" != *. ]] || \
        fail "Enter a production hostname without a scheme, port, or path."
    APP_IP_ADDRESS="$(read_setting "Ubuntu VM IPv4 address" "$ip_default")"
    is_ipv4 "$APP_IP_ADDRESS" || fail "Enter a usable IPv4 address assigned to the VM."
    ip -4 -o address show scope global | awk '{ split($4, address, "/"); print address[1] }' | \
        grep -Fqx "$APP_IP_ADDRESS" || fail "The address $APP_IP_ADDRESS is not assigned to this VM."
    COST_DB_SERVER="$(read_setting "SQL Server host and fixed TCP port" "${COST_DB_SERVER:-sqlserver.example.internal,1433}")"
    [[ "$COST_DB_SERVER" =~ ,[0-9]+$ && "$COST_DB_SERVER" != *\\* ]] || \
        fail "Use SQL Server host,port form; named instances are not supported."
    COST_DB_USERNAME="$(read_setting "SQL login" "${COST_DB_USERNAME:-cost_app_access}")"
    COST_ERP_DATABASE="$(read_setting "ERP database" "${COST_ERP_DATABASE:-M1_ME}")"
    validate_identifier "$COST_DB_USERNAME"
    validate_identifier "$COST_ERP_DATABASE"

    storage_choice="$(read_setting "Costing storage (database/schema)" "${COST_APP_STORAGE_MODE:-database}")"
    case "${storage_choice,,}" in
        database|d|1)
            COST_APP_STORAGE_MODE="database"
            COST_APP_DATABASE="$(read_setting "Dedicated costing database" "${COST_APP_DATABASE:-M2_ME}")"
            COST_APP_SCHEMA="dbo"
            [[ "$COST_APP_DATABASE" != "$COST_ERP_DATABASE" ]] || \
                fail "The dedicated costing database must differ from the ERP database."
            ;;
        schema|s|2|erp_schema)
            COST_APP_STORAGE_MODE="erp_schema"
            COST_APP_DATABASE="$COST_ERP_DATABASE"
            COST_APP_SCHEMA="$(read_setting "Costing schema inside $COST_ERP_DATABASE" "${COST_APP_SCHEMA:-CostCalculator}")"
            [[ "$COST_APP_SCHEMA" != "dbo" ]] || fail "ERP-schema mode requires a dedicated schema."
            ;;
        *) fail "Choose database or schema for costing storage." ;;
    esac
    validate_identifier "$COST_APP_DATABASE"
    validate_identifier "$COST_APP_SCHEMA"

    read -r -p "Temporarily bypass SQL Server certificate validation? [y/N]: " trust_answer
    if [[ "$trust_answer" =~ ^[Yy]$ ]]; then
        COST_DB_TRUST_SERVER_CERTIFICATE="true"
        printf 'WARNING: SQL Server certificate identity validation is disabled.\n' >&2
    else
        COST_DB_TRUST_SERVER_CERTIFICATE="false"
    fi
    COST_REPORT_COMPANY_NAME="$(read_setting "Report company name" "${COST_REPORT_COMPANY_NAME:-Meziere Enterprises}")"

    for value in "$APP_HOSTNAME" "$APP_IP_ADDRESS" "$COST_DB_SERVER" "$COST_DB_USERNAME" \
        "$COST_ERP_DATABASE" "$COST_APP_STORAGE_MODE" "$COST_APP_DATABASE" \
        "$COST_APP_SCHEMA" "$COST_REPORT_COMPANY_NAME"; do
        validate_config_value "$value"
    done

    local temporary_config
    temporary_config="$(mktemp "$config_dir/runtime.XXXXXX")"
    {
        write_environment_value APP_HOSTNAME "$APP_HOSTNAME"
        write_environment_value APP_IP_ADDRESS "$APP_IP_ADDRESS"
        write_environment_value COST_DB_SERVER "$COST_DB_SERVER"
        write_environment_value COST_DB_USERNAME "$COST_DB_USERNAME"
        write_environment_value COST_DB_DRIVER "ODBC Driver 18 for SQL Server"
        write_environment_value COST_ERP_DATABASE "$COST_ERP_DATABASE"
        write_environment_value COST_APP_STORAGE_MODE "$COST_APP_STORAGE_MODE"
        write_environment_value COST_APP_DATABASE "$COST_APP_DATABASE"
        write_environment_value COST_APP_SCHEMA "$COST_APP_SCHEMA"
        write_environment_value COST_DB_TRUST_SERVER_CERTIFICATE "$COST_DB_TRUST_SERVER_CERTIFICATE"
        write_environment_value COST_DB_CONNECTION_TIMEOUT_SECONDS "5"
        write_environment_value COST_REPORT_COMPANY_NAME "$COST_REPORT_COMPANY_NAME"
        write_environment_value COST_APP_USERS_JSON_FILE "$users_file"
        write_environment_value COST_DB_PASSWORD_FILE "$db_password_file"
        write_environment_value UPDATE_STATUS_FILE "$state_root/update/update-status.json"
        write_environment_value UPDATE_REQUEST_FILE "$state_root/update/update-request.json"
    } > "$temporary_config"
    chown root:"$service_group" "$temporary_config"
    chmod 0640 "$temporary_config"
    mv -f -- "$temporary_config" "$config_file"
}

write_caddy_config() {
    load_existing_config
    local temporary_config
    temporary_config="$(mktemp "$config_dir/caddy.XXXXXX")"
    {
        write_environment_value APP_HOSTNAME "$APP_HOSTNAME"
        write_environment_value APP_IP_ADDRESS "$APP_IP_ADDRESS"
    } > "$temporary_config"
    chown root:caddy "$temporary_config"
    chmod 0640 "$temporary_config"
    mv -f -- "$temporary_config" "$caddy_config_file"
}

create_db_password() {
    [[ ! -s "$db_password_file" || "$replace_db_password" == "true" ]] || return
    [[ -t 0 ]] || fail "$db_password_file is missing and input is not interactive."
    local password confirmation
    log "Creating the SQL password secret"
    read -r -s -p "SQL password: " password
    printf '\n'
    read -r -s -p "Confirm SQL password: " confirmation
    printf '\n'
    [[ -n "$password" && "$password" == "$confirmation" ]] || fail "SQL passwords did not match."
    printf '%s' "$password" > "$db_password_file"
    unset password confirmation
    chown root:"$service_group" "$db_password_file"
    chmod 0640 "$db_password_file"
}

create_initial_admin() {
    [[ -s "$users_file" ]] && return
    [[ -t 0 ]] || fail "$users_file is missing and input is not interactive."
    local username temporary_users
    log "Creating the initial application administrator"
    read -r -p "Administrator username: " username
    [[ "$username" =~ ^[A-Za-z0-9_.@-]{1,100}$ ]] || fail "The administrator username contains unsupported characters."
    temporary_users="$(mktemp "$state_root/users/app_users.XXXXXX")"
    (cd "$source_root" && "$app_python" -m tools.create_user_seed "$username") > "$temporary_users"
    chown "$service_user":"$service_group" "$temporary_users"
    chmod 0600 "$temporary_users"
    mv -f -- "$temporary_users" "$users_file"
}

render_database_setup() {
    load_existing_config
    local temporary_setup
    temporary_setup="$(mktemp "$state_root/database/reset-selected-storage.XXXXXX")"
    awk \
        -v storage_mode="$COST_APP_STORAGE_MODE" \
        -v app_database="$COST_APP_DATABASE" \
        -v app_schema="$COST_APP_SCHEMA" \
        -v db_username="$COST_DB_USERNAME" '
        BEGIN { schema_setup_written = 0 }
        /^USE \[M2_ME\];$/ {
            if (storage_mode == "database") {
                print "USE [master];"
                print "GO"
                print "IF DB_ID(N\047" app_database "\047) IS NULL"
                print "    EXEC(N\047CREATE DATABASE [" app_database "]\047);"
                print "GO"
            }
            print "USE [" app_database "];"
            next
        }
        /^SET ANSI_NULLS ON;$/ && !schema_setup_written {
            print "IF DB_NAME() <> N\047" app_database "\047"
            print "BEGIN"
            print "    RAISERROR(N\047Refusing to configure costing storage in the wrong database.\047, 16, 1);"
            print "    SET NOEXEC ON;"
            print "END;"
            print "GO"
            print "IF SCHEMA_ID(N\047" app_schema "\047) IS NULL"
            print "    EXEC(N\047CREATE SCHEMA [" app_schema "] AUTHORIZATION [dbo]\047);"
            print "GO"
            schema_setup_written = 1
        }
        {
            gsub(/dbo\./, "[" app_schema "].")
            print
        }
        END {
            print ""
            print "IF DATABASE_PRINCIPAL_ID(N\047" db_username "\047) IS NULL"
            print "    EXEC(N\047CREATE USER [" db_username "] FOR LOGIN [" db_username "]\047);"
            print "GO"
            print "GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::[" app_schema "] TO [" db_username "];"
            print "GO"
        }
    ' "$source_root/database/reset_schema.sql" > "$temporary_setup"
    chown root:"$service_group" "$temporary_setup"
    chmod 0640 "$temporary_setup"
    mv -f -- "$temporary_setup" "$database_setup_file"
}

if [[ ! -s "$config_file" || "$reconfigure" == "true" ]]; then
    [[ -t 0 ]] || fail "$config_file is missing or reconfiguration was requested without interactive input."
    log "Configuring the native VM application"
    write_runtime_config
else
    log "Keeping the existing runtime configuration"
fi
write_caddy_config
create_db_password
create_initial_admin
render_database_setup

log "Native VM configuration is ready"
printf 'Runtime configuration: %s\n' "$config_file"
printf 'Generated DBA setup script: %s\n' "$database_setup_file"
