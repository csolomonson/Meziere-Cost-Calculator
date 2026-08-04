#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
runtime_dir="$project_root/deployment/runtime"

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

on_error() {
    printf '\nDeployment stopped on line %s. The previous image and Docker volumes were retained.\n' "$1" >&2
    if command -v docker >/dev/null 2>&1; then
        (cd "$project_root" && docker compose ps && docker compose logs --tail=80 app proxy) >&2 || true
    fi
}
trap 'on_error "$LINENO"' ERR

require_root() {
    if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
        fail "Run this installer with sudo: sudo bash deployment/ubuntu/install.sh"
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

configure_environment() {
    local env_file="$project_root/.env"
    [[ -f "$env_file" ]] && return
    [[ -t 0 ]] || fail ".env is missing and input is not interactive. Create it from .env.example before deployment."

    log "Creating the non-secret deployment configuration"
    local app_hostname db_server db_username erp_database app_database app_version trust_certificate image_tag
    app_hostname="$(read_setting "Application DNS hostname" "$(hostname -f 2>/dev/null || hostname)")"
    [[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != .* && "$app_hostname" != *. ]] || fail "Enter a DNS hostname without a scheme, port, or path."
    db_server="$(read_setting "SQL Server host and fixed TCP port" "sqlserver.example.internal,1433")"
    [[ "$db_server" =~ ,[0-9]+$ ]] || fail "Use a fixed SQL Server TCP endpoint in host,port form; named instances are not supported from Linux."
    [[ "$db_server" != *\\* ]] || fail "Named SQL Server instances are not supported. Use host,port."
    db_username="$(read_setting "SQL login" "cost_app_access")"
    erp_database="$(read_setting "ERP database" "M1_ME")"
    app_database="$(read_setting "Costing database" "M2_ME")"
    app_version="$(read_setting "Application version" "2026.08.17")"
    read -r -p "Temporarily bypass SQL Server certificate validation? [y/N]: " trust_certificate
    if [[ "$trust_certificate" =~ ^[Yy]$ ]]; then
        trust_certificate="true"
        printf 'WARNING: TrustServerCertificate is enabled. Replace this with a trusted SQL Server certificate after initial validation.\n' >&2
    else
        trust_certificate="false"
    fi
    image_tag="cost-calculator:${app_version//[^A-Za-z0-9_.-]/-}"

    for value in "$app_hostname" "$db_server" "$db_username" "$erp_database" "$app_database" "$app_version" "$image_tag"; do
        [[ "$value" != *$'\n'* && "$value" != *$'\r'* && "$value" != *'#'* ]] || fail "Configuration values cannot contain line breaks or #."
    done

    umask 077
    {
        printf 'APP_HOSTNAME=%s\n' "$app_hostname"
        printf 'COST_DB_SERVER=%s\n' "$db_server"
        printf 'COST_DB_USERNAME=%s\n' "$db_username"
        printf 'COST_DB_DRIVER=ODBC Driver 18 for SQL Server\n'
        printf 'COST_ERP_DATABASE=%s\n' "$erp_database"
        printf 'COST_APP_DATABASE=%s\n' "$app_database"
        printf 'COST_DB_TRUST_SERVER_CERTIFICATE=%s\n' "$trust_certificate"
        printf 'COST_DB_CONNECTION_TIMEOUT_SECONDS=5\n'
        printf 'COST_APP_IMAGE=%s\n' "$image_tag"
        printf 'APP_VERSION=%s\n' "$app_version"
        printf 'APP_REPOSITORY=\n'
    } > "$env_file"
    chmod 0600 "$env_file"
}

env_value() {
    local key="$1"
    sed -n "s/^${key}=//p" "$project_root/.env" | tail -n 1 | tr -d '\r'
}

validate_environment() {
    local app_hostname db_server app_version image_tag
    app_hostname="$(env_value APP_HOSTNAME)"
    db_server="$(env_value COST_DB_SERVER)"
    app_version="$(env_value APP_VERSION)"
    image_tag="$(env_value COST_APP_IMAGE)"

    [[ "$app_hostname" =~ ^[A-Za-z0-9.-]+$ && "$app_hostname" != "localhost" ]] || fail ".env must set APP_HOSTNAME to the production DNS hostname."
    [[ "$db_server" =~ ,[0-9]+$ && "$db_server" != *\\* ]] || fail ".env must set COST_DB_SERVER in host,port form."
    [[ -n "$app_version" && "$app_version" != "development" ]] || fail ".env must set a release APP_VERSION."
    [[ "$image_tag" == cost-calculator:* && "$image_tag" != "cost-calculator:local" ]] || fail ".env must set a versioned COST_APP_IMAGE tag."
    if [[ "$(env_value COST_DB_TRUST_SERVER_CERTIFICATE)" == "true" ]]; then
        printf 'WARNING: SQL Server certificate identity validation is disabled in .env.\n' >&2
    fi
    chmod 0600 "$project_root/.env"
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

remember_previous_image() {
    local container_id previous_image new_image
    container_id="$(docker compose ps -q app 2>/dev/null || true)"
    [[ -n "$container_id" ]] || return 0
    previous_image="$(docker inspect --format '{{.Config.Image}}' "$container_id")"
    new_image="$(env_value COST_APP_IMAGE)"
    if [[ -n "$previous_image" && "$previous_image" != "$new_image" ]]; then
        mkdir -p "$runtime_dir"
        printf '%s\n' "$previous_image" > "$runtime_dir/previous-image"
        chmod 0600 "$runtime_dir/previous-image"
    fi
}

deploy() {
    local app_hostname current_container current_image desired_image
    cd "$project_root"
    docker compose config --quiet

    desired_image="$(env_value COST_APP_IMAGE)"
    current_container="$(docker compose ps -q app 2>/dev/null || true)"
    current_image=""
    if [[ -n "$current_container" ]]; then
        current_image="$(docker inspect --format '{{.Config.Image}}' "$current_container")"
    fi
    if [[ "$current_image" == "$desired_image" ]] || docker image inspect "$desired_image" >/dev/null 2>&1; then
        log "Image $desired_image already exists; retaining the immutable build"
    else
        log "Building the versioned application image $desired_image"
        docker compose build --pull app
    fi
    grant_secret_access_to_app
    create_initial_admin_if_needed

    log "Testing credentials, SQL connectivity, schema, and PDF runtime"
    docker compose run --rm --no-deps app python -m tools.deployment_preflight

    remember_previous_image
    log "Starting the application and waiting for database-aware readiness"
    docker compose up -d --wait --remove-orphans
    app_hostname="$(env_value APP_HOSTNAME)"
    curl --fail --silent --show-error --insecure --resolve "$app_hostname:443:127.0.0.1" "https://$app_hostname/api/ready" >/dev/null

    mkdir -p "$runtime_dir"
    docker compose cp proxy:/data/caddy/pki/authorities/local/root.crt "$runtime_dir/caddy-root.crt"
    chmod 0644 "$runtime_dir/caddy-root.crt"
}

main() {
    require_root
    require_ubuntu
    cd "$project_root"
    mkdir -p "$runtime_dir"
    install_docker
    configure_environment
    validate_environment
    create_secrets
    deploy

    log "Deployment succeeded"
    docker compose ps
    printf '\nApplication URL: https://%s/\n' "$(env_value APP_HOSTNAME)"
    printf 'Client trust certificate: %s\n' "$runtime_dir/caddy-root.crt"
    printf 'Verification command: sudo bash deployment/ubuntu/verify.sh\n'
    printf 'Rollback command: sudo bash deployment/ubuntu/rollback.sh\n'
}

main "$@"
