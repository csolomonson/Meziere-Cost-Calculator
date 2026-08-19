#!/usr/bin/env bash
set -Eeuo pipefail

state_root="${COST_APP_STATE_ROOT:-/var/lib/cost-calculator}"
config_file="$state_root/config/runtime.env"
users_file="$state_root/users/app_users.json"
db_password_file="$state_root/secrets/db_password.txt"
extra_ca_file="$state_root/ca/extra-ca.crt"
ca_bundle="$state_root/ca/ca-certificates.crt"
database_setup_file="$state_root/database/reset-selected-storage.sql"

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

ensure_state_directories() {
    mkdir -p \
        "$state_root/config" \
        "$state_root/secrets" \
        "$state_root/users" \
        "$state_root/ca" \
        "$state_root/database" \
        "$state_root/caddy/data" \
        "$state_root/caddy/config" \
        "$state_root/update"
    chmod 0700 "$state_root/config" "$state_root/secrets" "$state_root/users" "$state_root/ca"
}

existing_value() {
    local key="$1"
    [[ -r "$config_file" ]] || return 0
    sed -n "s/^${key}=//p" "$config_file" | tail -n 1 | tr -d '\r'
}

configured_or_default() {
    local key="$1"
    local fallback="$2"
    local configured
    configured="$(existing_value "$key")"
    printf '%s' "${configured:-$fallback}"
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

validate_identifier() {
    [[ "$1" =~ ^[A-Za-z_][A-Za-z0-9_@\$-]{0,127}$ ]] || fail "Unsupported SQL identifier: $1"
}

validate_config_value() {
    [[ "$1" != *$'\n'* && "$1" != *$'\r'* && "$1" != *'#'* ]] || fail "Configuration values cannot contain line breaks or #."
}

rebuild_ca_bundle() {
    local system_bundle="/usr/local/share/cost-calculator/ca-certificates.crt"
    local temporary_bundle
    [[ -s "$system_bundle" ]] || fail "The image CA certificate bundle is missing."
    temporary_bundle="$(mktemp "$state_root/ca/ca-certificates.XXXXXX")"
    cp "$system_bundle" "$temporary_bundle"
    if [[ -s "$extra_ca_file" ]]; then
        printf '\n' >> "$temporary_bundle"
        cat "$extra_ca_file" >> "$temporary_bundle"
    fi
    chmod 0600 "$temporary_bundle"
    mv -f -- "$temporary_bundle" "$ca_bundle"
}

install_ca() {
    ensure_state_directories
    local temporary_ca
    temporary_ca="$(mktemp "$state_root/ca/extra-ca.XXXXXX")"
    if [[ "$#" -eq 1 ]]; then
        [[ -r "$1" ]] || fail "Cannot read CA certificate file: $1"
        cp "$1" "$temporary_ca"
    elif [[ "$#" -eq 0 ]]; then
        cat > "$temporary_ca"
    else
        fail "Usage: install-ca [PEM_FILE], or provide PEM data on standard input."
    fi
    grep -q -- '-----BEGIN CERTIFICATE-----' "$temporary_ca" || fail "The supplied file does not contain a PEM certificate."
    chmod 0600 "$temporary_ca"
    mv -f -- "$temporary_ca" "$extra_ca_file"
    rebuild_ca_bundle
    log "Installed the SQL Server CA certificate bundle"
}

render_database_setup() {
    local storage_mode="$1"
    local app_database="$2"
    local app_schema="$3"
    local db_username="$4"
    local source_sql="/app/database/reset_schema.sql"

    awk \
        -v storage_mode="$storage_mode" \
        -v app_database="$app_database" \
        -v app_schema="$app_schema" \
        -v db_username="$db_username" '
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
    ' "$source_sql" > "$database_setup_file"
    chmod 0600 "$database_setup_file"
}

configure() {
    [[ "$#" -eq 0 ]] || fail "Usage: configure"
    [[ -t 0 ]] || fail "The configure command requires an interactive terminal. Use docker run --rm -it."
    ensure_state_directories

    log "Configuring the single-container application"
    local app_hostname app_ip_address db_server db_username erp_database storage_choice storage_mode app_database app_schema trust_certificate company_name
    app_hostname="$(read_setting "Application DNS hostname" "$(configured_or_default APP_HOSTNAME cost-calculator.local)")"
    [[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != "localhost" && "$app_hostname" != .* && "$app_hostname" != *. ]] || fail "Enter a production hostname without a scheme, port, or path."

    app_ip_address="$(read_setting "Ubuntu server IPv4 address" "$(existing_value APP_IP_ADDRESS || true)")"
    is_ipv4 "$app_ip_address" || fail "Enter the usable IPv4 address assigned to the Ubuntu server."
    db_server="$(read_setting "SQL Server host and fixed TCP port" "$(configured_or_default COST_DB_SERVER 'sqlserver.example.internal,1433')")"
    [[ "$db_server" =~ ,[0-9]+$ && "$db_server" != *\\* ]] || fail "Use SQL Server host,port form; named instances are not supported."
    db_username="$(read_setting "SQL login" "$(configured_or_default COST_DB_USERNAME cost_app_access)")"
    erp_database="$(read_setting "ERP database" "$(configured_or_default COST_ERP_DATABASE M1_ME)")"
    validate_identifier "$db_username"
    validate_identifier "$erp_database"

    storage_choice="$(read_setting "Costing storage (database/schema)" "$(configured_or_default COST_APP_STORAGE_MODE database)")"
    case "${storage_choice,,}" in
        database|d|1)
            storage_mode="database"
            app_database="$(read_setting "Dedicated costing database" "$(configured_or_default COST_APP_DATABASE M2_ME)")"
            app_schema="dbo"
            [[ "$app_database" != "$erp_database" ]] || fail "The dedicated costing database must differ from the ERP database."
            ;;
        schema|s|2|erp_schema)
            storage_mode="erp_schema"
            app_database="$erp_database"
            app_schema="$(read_setting "Costing schema inside $erp_database" "$(configured_or_default COST_APP_SCHEMA CostCalculator)")"
            [[ "$app_schema" != "dbo" ]] || fail "ERP-schema mode requires a dedicated schema instead of dbo."
            ;;
        *) fail "Choose database or schema for costing storage." ;;
    esac
    validate_identifier "$app_database"
    validate_identifier "$app_schema"

    local trust_default trust_answer trust_prompt
    trust_default="$(configured_or_default COST_DB_TRUST_SERVER_CERTIFICATE false)"
    if [[ "$trust_default" == "true" ]]; then
        trust_prompt="Temporarily bypass SQL Server certificate validation? [Y/n]: "
    else
        trust_prompt="Temporarily bypass SQL Server certificate validation? [y/N]: "
    fi
    read -r -p "$trust_prompt" trust_answer
    if [[ -z "$trust_answer" ]]; then
        trust_certificate="$trust_default"
    elif [[ "$trust_answer" =~ ^[Yy]$ ]]; then
        trust_certificate="true"
    else
        trust_certificate="false"
    fi
    if [[ "$trust_certificate" == "true" ]]; then
        printf 'WARNING: SQL Server certificate identity validation is disabled.\n' >&2
    fi
    company_name="$(read_setting "Report company name" "$(configured_or_default COST_REPORT_COMPANY_NAME 'Meziere Enterprises')")"

    for value in "$app_hostname" "$app_ip_address" "$db_server" "$db_username" "$erp_database" "$storage_mode" "$app_database" "$app_schema" "$company_name"; do
        validate_config_value "$value"
    done

    local temporary_config
    temporary_config="$(mktemp "$state_root/config/runtime.XXXXXX")"
    {
        printf 'APP_HOSTNAME=%s\n' "$app_hostname"
        printf 'APP_IP_ADDRESS=%s\n' "$app_ip_address"
        printf 'COST_DB_SERVER=%s\n' "$db_server"
        printf 'COST_DB_USERNAME=%s\n' "$db_username"
        printf 'COST_DB_DRIVER=ODBC Driver 18 for SQL Server\n'
        printf 'COST_ERP_DATABASE=%s\n' "$erp_database"
        printf 'COST_APP_STORAGE_MODE=%s\n' "$storage_mode"
        printf 'COST_APP_DATABASE=%s\n' "$app_database"
        printf 'COST_APP_SCHEMA=%s\n' "$app_schema"
        printf 'COST_DB_TRUST_SERVER_CERTIFICATE=%s\n' "$trust_certificate"
        printf 'COST_DB_CONNECTION_TIMEOUT_SECONDS=5\n'
        printf 'COST_REPORT_COMPANY_NAME=%s\n' "$company_name"
    } > "$temporary_config"
    chmod 0600 "$temporary_config"
    mv -f -- "$temporary_config" "$config_file"

    local replace_password db_password db_password_confirm
    replace_password="y"
    if [[ -s "$db_password_file" ]]; then
        read -r -p "Replace the stored SQL password? [y/N]: " replace_password
    fi
    if [[ "$replace_password" =~ ^[Yy]$ ]]; then
        read -r -s -p "SQL password: " db_password
        printf '\n'
        read -r -s -p "Confirm SQL password: " db_password_confirm
        printf '\n'
        [[ -n "$db_password" && "$db_password" == "$db_password_confirm" ]] || fail "SQL passwords did not match."
        printf '%s' "$db_password" > "$db_password_file"
        chmod 0600 "$db_password_file"
        unset db_password db_password_confirm
    fi

    if [[ ! -s "$users_file" ]]; then
        local admin_username temporary_users
        read -r -p "Initial administrator username: " admin_username
        [[ "$admin_username" =~ ^[A-Za-z0-9_.@-]{1,100}$ ]] || fail "The administrator username contains unsupported characters."
        temporary_users="$(mktemp "$state_root/users/app_users.XXXXXX")"
        python -m tools.create_user_seed "$admin_username" > "$temporary_users"
        chmod 0600 "$temporary_users"
        mv -f -- "$temporary_users" "$users_file"
    else
        log "Keeping the existing application users"
    fi

    rebuild_ca_bundle
    render_database_setup "$storage_mode" "$app_database" "$app_schema" "$db_username"

    log "Configuration was saved in the Docker volume"
    printf 'To export the DBA setup script:\n'
    printf '  docker run --rm -v cost-calculator-data:%s IMAGE database-setup > reset-selected-storage.sql\n' "$state_root"
    printf 'Start the application after the database owner has prepared the schema.\n'

    if /app/deployment/container-entrypoint.sh preflight; then
        log "Configuration and preflight succeeded"
    else
        printf '\nPreflight failed. If the costing schema is new, export and run the DBA setup script, then retry preflight.\n' >&2
        exit 1
    fi
}

case "${1:-}" in
    configure)
        shift
        configure "$@"
        ;;
    install-ca)
        shift
        install_ca "$@"
        ;;
    *) fail "Expected configure or install-ca." ;;
esac
