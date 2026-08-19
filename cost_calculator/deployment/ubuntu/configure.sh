#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
runtime_dir="$project_root/deployment/runtime"
release_file="$project_root/deployment/release.env"
configure_storage_requested=false

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    printf 'Usage: sudo bash deployment/ubuntu/configure.sh [--configure-storage]\n'
    printf 'Use --configure-storage to replace the existing database/schema selection.\n'
}

parse_args() {
    [[ "$#" -le 1 ]] || {
        usage >&2
        exit 2
    }
    case "${1:-}" in
        "") ;;
        --configure-storage) configure_storage_requested=true ;;
        --help|-h)
            usage
            exit 0
            ;;
        *) fail "Unknown configuration option: $1" ;;
    esac
}

on_error() {
    printf '\nConfiguration stopped on line %s. The previous containers and Docker volumes were retained.\n' "$1" >&2
    if command -v docker >/dev/null 2>&1; then
        (cd "$project_root" && docker compose ps && docker compose logs --tail=80 app proxy) >&2 || true
    fi
}
trap 'on_error "$LINENO"' ERR

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        fail "Run this script with sudo: sudo bash deployment/ubuntu/configure.sh"
    fi
}

require_ubuntu() {
    [[ -r /etc/os-release ]] || fail "Cannot identify this operating system."
    # shellcheck disable=SC1091
    . /etc/os-release
    [[ "${ID:-}" == "ubuntu" ]] || fail "This installer supports Ubuntu Server only."
    case "${VERSION_ID:-}" in
        22.04|24.04|26.04) ;;
        *) fail "Ubuntu ${VERSION_ID:-unknown} is not a supported Docker target for this release." ;;
    esac
    [[ "$(dpkg --print-architecture)" =~ ^(amd64|arm64)$ ]] || fail "Only amd64 and arm64 VMs are supported."
}

install_docker() {
    if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
        log "Docker Engine and Compose are already installed"
        systemctl enable --now docker
        return
    fi

    export DEBIAN_FRONTEND=noninteractive
    apt-get update
    apt-get install -y ca-certificates curl

    for conflicting_package in docker.io docker-compose docker-compose-v2 podman-docker containerd runc; do
        if dpkg-query -W -f='${Status}' "$conflicting_package" 2>/dev/null | grep -q "install ok installed"; then
            fail "Conflicting package '$conflicting_package' is installed. Remove it during the VM preparation window, then rerun this installer."
        fi
    done

    log "Installing Docker Engine from Docker's official Ubuntu repository"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # shellcheck disable=SC1091
    . /etc/os-release
    architecture="$(dpkg --print-architecture)"
    codename="${UBUNTU_CODENAME:-$VERSION_CODENAME}"
    printf '%s\n' \
        "Types: deb" \
        "URIs: https://download.docker.com/linux/ubuntu" \
        "Suites: $codename" \
        "Components: stable" \
        "Architectures: $architecture" \
        "Signed-By: /etc/apt/keyrings/docker.asc" \
        > /etc/apt/sources.list.d/docker.sources

    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    docker version >/dev/null
    docker compose version
}

read_setting() {
    local prompt="$1"
    local default_value="$2"
    local result
    read -r -p "$prompt [$default_value]: " result
    printf '%s' "${result:-$default_value}"
}

release_value() {
    local key="$1"
    [[ -f "$release_file" ]] || return 0
    sed -n "s/^${key}=//p" "$release_file" | tail -n 1 | tr -d '\r'
}

sync_release_settings() {
    [[ -f "$release_file" ]] || return 0

    local app_version image_ref repository env_file temporary_env
    app_version="$(release_value APP_VERSION)"
    image_ref="$(release_value COST_APP_IMAGE)"
    repository="$(release_value APP_REPOSITORY)"
    env_file="$project_root/.env"

    [[ "$app_version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?$ ]] || fail "deployment/release.env contains an invalid APP_VERSION."
    [[ "$image_ref" =~ ^ghcr\.io/[a-z0-9._/-]+:[A-Za-z0-9_.-]+@sha256:[a-f0-9]{64}$ ]] || fail "deployment/release.env must select an immutable GHCR image by tag and digest."
    [[ "$repository" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || fail "deployment/release.env contains an invalid APP_REPOSITORY."

    temporary_env="$(mktemp "$project_root/.env.release.XXXXXX")"
    awk -v app_version="$app_version" -v image_ref="$image_ref" -v repository="$repository" '
        /^APP_VERSION=/ {
            if (!version_written) print "APP_VERSION=" app_version
            version_written = 1
            next
        }
        /^COST_APP_IMAGE=/ {
            if (!image_written) print "COST_APP_IMAGE=" image_ref
            image_written = 1
            next
        }
        /^APP_REPOSITORY=/ {
            if (!repository_written) print "APP_REPOSITORY=" repository
            repository_written = 1
            next
        }
        { print }
        END {
            if (!version_written) print "APP_VERSION=" app_version
            if (!image_written) print "COST_APP_IMAGE=" image_ref
            if (!repository_written) print "APP_REPOSITORY=" repository
        }
    ' "$env_file" > "$temporary_env"
    chown --reference="$env_file" "$temporary_env"
    chmod --reference="$env_file" "$temporary_env"
    mv -f -- "$temporary_env" "$env_file"
    log "Selected release $app_version ($image_ref)"
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
        return 0
    fi
    for candidate in $(hostname -I 2>/dev/null); do
        if is_ipv4 "$candidate"; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    return 1
}

configure_environment() {
    local env_file="$project_root/.env"
    if [[ -f "$env_file" ]]; then
        if [[ "$configure_storage_requested" == "true" ]]; then
            reconfigure_storage
        fi
        return
    fi
    [[ -f "$release_file" ]] || fail "deployment/release.env is missing. Deploy from a GitHub release bundle."
    [[ -t 0 ]] || fail ".env is missing and input is not interactive. Create it from .env.example before deployment."

    log "Creating the non-secret deployment configuration"
    local app_hostname app_ip_address app_ip_default db_server db_username erp_database app_database app_schema storage_choice storage_mode app_version trust_certificate image_ref repository
    app_hostname="$(read_setting "Application DNS hostname" "$(hostname -f 2>/dev/null || hostname)")"
    [[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != .* && "$app_hostname" != *. ]] || fail "Enter a DNS hostname without a scheme, port, or path."
    app_ip_default="$(detect_primary_ipv4)" || fail "Could not detect the VM IPv4 address. Configure networking, then rerun the installer."
    app_ip_address="$(read_setting "Application VM IPv4 address" "$app_ip_default")"
    is_ipv4 "$app_ip_address" || fail "Enter a usable IPv4 address assigned to this VM."
    db_server="$(read_setting "SQL Server host and fixed TCP port" "sqlserver.example.internal,1433")"
    [[ "$db_server" =~ ,[0-9]+$ ]] || fail "Use a fixed SQL Server TCP endpoint in host,port form; named instances are not supported from Linux."
    [[ "$db_server" != *\\* ]] || fail "Named SQL Server instances are not supported. Use host,port."
    db_username="$(read_setting "SQL login" "cost_app_access")"
    erp_database="$(read_setting "ERP database" "M1_ME")"
    storage_choice="$(read_setting "Costing storage: separate database or schema in ERP database (database/schema)" "database")"
    case "${storage_choice,,}" in
        database|d|1)
            storage_mode="database"
            app_database="$(read_setting "Dedicated costing database" "M2_ME")"
            app_schema="dbo"
            ;;
        schema|s|2|erp_schema)
            storage_mode="erp_schema"
            app_database="$erp_database"
            app_schema="$(read_setting "Costing schema within $erp_database" "CostCalculator")"
            ;;
        *) fail "Choose 'database' or 'schema' for costing storage." ;;
    esac
    app_version="$(release_value APP_VERSION)"
    image_ref="$(release_value COST_APP_IMAGE)"
    repository="$(release_value APP_REPOSITORY)"
    read -r -p "Temporarily bypass SQL Server certificate validation? [y/N]: " trust_certificate
    if [[ "$trust_certificate" =~ ^[Yy]$ ]]; then
        trust_certificate="true"
        printf 'WARNING: TrustServerCertificate is enabled. Replace this with a trusted SQL Server certificate after initial validation.\n' >&2
    else
        trust_certificate="false"
    fi
    for value in "$app_hostname" "$app_ip_address" "$db_server" "$db_username" "$erp_database" "$storage_mode" "$app_database" "$app_schema" "$app_version" "$image_ref" "$repository"; do
        [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *'#'* ]] || fail "Configuration values cannot contain line breaks or #."
    done

    umask 077
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
        printf 'COST_APP_IMAGE=%s\n' "$image_ref"
        printf 'APP_VERSION=%s\n' "$app_version"
        printf 'APP_REPOSITORY=%s\n' "$repository"
    } > "$env_file"
    chmod 0600 "$env_file"
}

ensure_network_settings() {
    local env_file="$project_root/.env"
    local app_ip_address
    app_ip_address="$(env_value APP_IP_ADDRESS)"
    if [[ -z "$app_ip_address" ]]; then
        app_ip_address="$(detect_primary_ipv4)" || fail "APP_IP_ADDRESS is missing and the VM IPv4 address could not be detected."
        printf 'APP_IP_ADDRESS=%s\n' "$app_ip_address" >> "$env_file"
        chmod 0600 "$env_file"
        log "Added the detected VM IPv4 address $app_ip_address to .env"
    fi
}

write_storage_settings() {
    local storage_mode="$1"
    local app_database="$2"
    local app_schema="$3"
    local env_file="$project_root/.env"
    local temporary_env
    temporary_env="$(mktemp "$project_root/.env.storage.XXXXXX")"
    awk \
        -v storage_mode="$storage_mode" \
        -v app_database="$app_database" \
        -v app_schema="$app_schema" '
        /^COST_APP_STORAGE_MODE=/ {
            if (!mode_written) print "COST_APP_STORAGE_MODE=" storage_mode
            mode_written = 1
            next
        }
        /^COST_APP_DATABASE=/ {
            if (!database_written) print "COST_APP_DATABASE=" app_database
            database_written = 1
            next
        }
        /^COST_APP_SCHEMA=/ {
            if (!schema_written) print "COST_APP_SCHEMA=" app_schema
            schema_written = 1
            next
        }
        { print }
        END {
            if (!mode_written) print "COST_APP_STORAGE_MODE=" storage_mode
            if (!database_written) print "COST_APP_DATABASE=" app_database
            if (!schema_written) print "COST_APP_SCHEMA=" app_schema
        }
    ' "$env_file" > "$temporary_env"
    chown --reference="$env_file" "$temporary_env"
    chmod --reference="$env_file" "$temporary_env"
    mv -f -- "$temporary_env" "$env_file"
}

reconfigure_storage() {
    [[ -t 0 ]] || fail "--configure-storage requires interactive input."
    local erp_database current_app_database storage_choice storage_mode app_database app_schema database_default
    erp_database="$(env_value COST_ERP_DATABASE)"
    current_app_database="$(env_value COST_APP_DATABASE)"
    database_default="$current_app_database"
    [[ -n "$database_default" && "$database_default" != "$erp_database" ]] || database_default="M2_ME"

    log "Selecting new costing storage; existing data is not migrated"
    storage_choice="$(read_setting "Costing storage: separate database or schema in ERP database (database/schema)" "database")"
    case "${storage_choice,,}" in
        database|d|1)
            storage_mode="database"
            app_database="$(read_setting "Dedicated costing database" "$database_default")"
            app_schema="dbo"
            ;;
        schema|s|2|erp_schema)
            storage_mode="erp_schema"
            app_database="$erp_database"
            app_schema="$(read_setting "Costing schema within $erp_database" "CostCalculator")"
            ;;
        *) fail "Choose 'database' or 'schema' for costing storage." ;;
    esac
    write_storage_settings "$storage_mode" "$app_database" "$app_schema"
}

ensure_storage_settings() {
    local env_file="$project_root/.env"
    local app_database erp_database app_schema storage_mode
    app_database="$(env_value COST_APP_DATABASE)"
    erp_database="$(env_value COST_ERP_DATABASE)"
    app_schema="$(env_value COST_APP_SCHEMA)"
    if [[ -z "$app_schema" ]]; then
        app_schema="dbo"
        printf 'COST_APP_SCHEMA=%s\n' "$app_schema" >> "$env_file"
    fi
    storage_mode="$(env_value COST_APP_STORAGE_MODE)"
    if [[ -z "$storage_mode" ]]; then
        if [[ "$app_database" == "$erp_database" && "$app_schema" != "dbo" ]]; then
            storage_mode="erp_schema"
        else
            storage_mode="database"
        fi
        printf 'COST_APP_STORAGE_MODE=%s\n' "$storage_mode" >> "$env_file"
    fi
    chmod 0600 "$env_file"
}

env_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$project_root/.env" | tail -n 1 | tr -d '\r'
}

validate_environment() {
    local app_hostname app_ip_address db_server db_username erp_database storage_mode app_database app_schema app_version image_tag
    app_hostname="$(env_value APP_HOSTNAME)"
    app_ip_address="$(env_value APP_IP_ADDRESS)"
    db_server="$(env_value COST_DB_SERVER)"
    db_username="$(env_value COST_DB_USERNAME)"
    erp_database="$(env_value COST_ERP_DATABASE)"
    storage_mode="$(env_value COST_APP_STORAGE_MODE)"
    app_database="$(env_value COST_APP_DATABASE)"
    app_schema="$(env_value COST_APP_SCHEMA)"
    app_version="$(env_value APP_VERSION)"
    image_tag="$(env_value COST_APP_IMAGE)"

    [[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != "localhost" ]] || fail ".env must set APP_HOSTNAME to the production DNS hostname."
    is_ipv4 "$app_ip_address" || fail ".env must set APP_IP_ADDRESS to a usable IPv4 address assigned to this VM."
    ip -4 -o address show scope global | awk '{ split($4, address, "/"); print address[1] }' | grep -Fqx "$app_ip_address" || fail "APP_IP_ADDRESS ($app_ip_address) is not assigned to this VM."
    [[ "$db_server" =~ ,[0-9]+$ && "$db_server" != *\\* ]] || fail ".env must set COST_DB_SERVER in host,port form."
    for identifier in "$db_username" "$erp_database" "$app_database" "$app_schema"; do
        [[ "$identifier" =~ ^[A-Za-z_][A-Za-z0-9_@\$-]{0,127}$ ]] || fail "Database, schema, and SQL login names must use supported SQL identifier characters."
    done
    case "$storage_mode" in
        database)
            [[ "$app_database" != "$erp_database" ]] || fail "Database storage mode requires a dedicated COST_APP_DATABASE different from COST_ERP_DATABASE."
            ;;
        erp_schema)
            [[ "$app_database" == "$erp_database" ]] || fail "ERP-schema storage mode requires COST_APP_DATABASE to match COST_ERP_DATABASE."
            [[ "$app_schema" != "dbo" ]] || fail "ERP-schema storage mode requires a dedicated schema instead of dbo."
            ;;
        *) fail ".env must set COST_APP_STORAGE_MODE to database or erp_schema." ;;
    esac
    [[ "$app_version" =~ ^v?[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?$ ]] || fail ".env must set a semantic release APP_VERSION."
    [[ "$image_tag" =~ ^ghcr\.io/[a-z0-9._/-]+:[A-Za-z0-9_.-]+@sha256:[a-f0-9]{64}$ ]] || fail ".env must select an immutable GHCR image by tag and digest."
    if [[ "$(env_value COST_DB_TRUST_SERVER_CERTIFICATE)" == "true" ]]; then
        printf 'WARNING: SQL Server certificate identity validation is disabled in .env.\n' >&2
    fi
    chmod 0600 "$project_root/.env"
}

render_database_setup() {
    local source_sql="$project_root/database/reset_schema.sql"
    local output_sql="$runtime_dir/reset-selected-storage.sql"
    local storage_mode app_database app_schema db_username
    storage_mode="$(env_value COST_APP_STORAGE_MODE)"
    app_database="$(env_value COST_APP_DATABASE)"
    app_schema="$(env_value COST_APP_SCHEMA)"
    db_username="$(env_value COST_DB_USERNAME)"

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
    ' "$source_sql" > "$output_sql"
    chmod 0644 "$output_sql"
    log "Prepared the destructive database setup script for $app_database.$app_schema"
    printf 'For new or disposable storage only, have a database administrator review and run: %s\n' "$output_sql"
}

create_secrets() {
    local secrets_dir="$project_root/secrets"
    local db_password_file="$secrets_dir/db_password.txt"
    local users_file="$secrets_dir/app_users.json"
    mkdir -p "$secrets_dir"
    chmod 0700 "$secrets_dir"
    umask 077

    if [[ ! -s "$db_password_file" ]]; then
        [[ -t 0 ]] || fail "$db_password_file is missing and input is not interactive."
        log "Creating the SQL password secret"
        local db_password db_password_confirm
        read -r -s -p "SQL password: " db_password
        printf '\n'
        read -r -s -p "Confirm SQL password: " db_password_confirm
        printf '\n'
        [[ -n "$db_password" && "$db_password" == "$db_password_confirm" ]] || fail "SQL passwords did not match."
        printf '%s' "$db_password" > "$db_password_file"
        unset db_password db_password_confirm
        chmod 0600 "$db_password_file"
    fi

    if [[ ! -s "$users_file" ]]; then
        printf '{}\n' > "$users_file"
        chmod 0600 "$users_file"
    fi
    chmod 0600 "$db_password_file" "$users_file"
}

prepare_ca_bundle() {
    local system_bundle="/etc/ssl/certs/ca-certificates.crt"
    local output_bundle="$runtime_dir/ca-certificates.crt"
    local temporary_bundle certificate
    [[ -s "$system_bundle" ]] || fail "The Ubuntu CA certificate bundle is missing."

    temporary_bundle="$(mktemp "$runtime_dir/ca-certificates.XXXXXX")"
    cp "$system_bundle" "$temporary_bundle"
    shopt -s nullglob
    for certificate in "$project_root"/deployment/sql-ca/*.crt; do
        printf '\n' >> "$temporary_bundle"
        cat "$certificate" >> "$temporary_bundle"
        log "Added SQL Server trust certificate $(basename "$certificate")"
    done
    shopt -u nullglob
    chmod 0444 "$temporary_bundle"
    mv -f -- "$temporary_bundle" "$output_bundle"
}

pull_release_images() {
    cd "$project_root"
    docker compose config --quiet
    log "Pulling the immutable application release and Caddy proxy images"
    docker compose pull app proxy
}

create_initial_admin_if_needed() {
    local users_file="$project_root/secrets/app_users.json"
    if ! grep -Eq '"[^"[:space:]]+"[[:space:]]*:' "$users_file"; then
        [[ -t 0 ]] || fail "$users_file does not contain a user and input is not interactive."
        log "Creating the initial application administrator"
        local admin_username seed_json
        read -r -p "Administrator username: " admin_username
        [[ "$admin_username" =~ ^[A-Za-z0-9_.@-]{1,100}$ ]] || fail "The administrator username contains unsupported characters."
        seed_json="$(docker compose run --rm --no-deps app python -m tools.create_user_seed "$admin_username")"
        [[ "$seed_json" == \{* ]] || fail "The administrator seed was not generated successfully."
        printf '%s\n' "$seed_json" > "$users_file"
        chmod 0400 "$users_file"
    fi
}

grant_secret_access_to_app() {
    local secrets_dir="$project_root/secrets"
    local app_uid app_gid
    app_uid="$(docker compose run --rm --no-deps --entrypoint id app -u | tr -d '\r\n')"
    app_gid="$(docker compose run --rm --no-deps --entrypoint id app -g | tr -d '\r\n')"
    [[ "$app_uid" =~ ^[0-9]+$ && "$app_gid" =~ ^[0-9]+$ ]] || fail "Could not determine the application container UID and GID."

    # File-backed Compose secrets are bind mounts, so their host ownership is
    # preserved inside the container. Grant only the non-root application user
    # read access instead of making either secret world-readable.
    chown "$app_uid:$app_gid" "$secrets_dir/db_password.txt" "$secrets_dir/app_users.json"
    chmod 0400 "$secrets_dir/db_password.txt" "$secrets_dir/app_users.json"
}

configure_runtime() {
    cd "$project_root"
    grant_secret_access_to_app
    create_initial_admin_if_needed

    log "Testing credentials, SQL connectivity, schema, and PDF runtime"
    docker compose run --rm --no-deps app python -m tools.deployment_preflight
}

main() {
    parse_args "$@"
    require_root
    require_ubuntu
    cd "$project_root"
    mkdir -p "$runtime_dir"
    install_docker
    configure_environment
    sync_release_settings
    ensure_network_settings
    ensure_storage_settings
    validate_environment
    render_database_setup
    create_secrets
    prepare_ca_bundle
    pull_release_images
    configure_runtime

    log "Startup configuration succeeded"
    printf 'Configured application release: %s\n' "$(env_value COST_APP_IMAGE)"
    printf 'Destructive database setup reference (do not rerun against retained data): %s\n' "$runtime_dir/reset-selected-storage.sql"
    printf 'Start command: sudo bash deployment/ubuntu/start.sh --skip-configure\n'
}

main "$@"
