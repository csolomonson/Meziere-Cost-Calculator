#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
install_root="/opt/cost-calculator"
config_dir="/etc/cost-calculator"
state_root="/var/lib/cost-calculator"
service_user="cost-calculator"
service_group="cost-calculator"
staging_dir=""

log() {
    printf '\n==> %s\n' "$*"
}

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

cleanup() {
    [[ -z "$staging_dir" || ! -e "$staging_dir" ]] || rm -rf -- "$staging_dir"
}
trap cleanup EXIT

require_host() {
    [[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/install.sh"
    [[ -r /etc/os-release ]] || fail "Cannot identify this operating system."
    # shellcheck disable=SC1091
    source /etc/os-release
    [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "24.04" ]] || \
        fail "The native deployment supports Ubuntu Server 24.04 LTS."
    [[ "$(dpkg --print-architecture)" =~ ^(amd64|arm64)$ ]] || fail "Only amd64 and arm64 VMs are supported."
}

install_host_packages() {
    export DEBIAN_FRONTEND=noninteractive
    log "Installing native VM prerequisites"
    apt-get update
    apt-get install -y apt-transport-https ca-certificates curl debian-archive-keyring debian-keyring gnupg \
        python3 python3-pip python3-venv build-essential git unixodbc unixodbc-dev

    local node_major
    node_major="$(node --version 2>/dev/null | sed -E 's/^v([0-9]+).*/\1/' || true)"
    if [[ -n "$node_major" && "$node_major" != "22" ]]; then
        fail "Node.js 22 is required by pnpm 11; remove the existing Node.js $node_major packages and rerun the installer."
    fi
    if [[ "$node_major" != "22" ]]; then
        local architecture
        architecture="$(dpkg --print-architecture)"
        install -d -m 0755 /usr/share/keyrings
        curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | \
            gpg --dearmor --yes -o /usr/share/keyrings/nodesource.gpg
        chmod a+r /usr/share/keyrings/nodesource.gpg
        {
            printf 'Types: deb\n'
            printf 'URIs: https://deb.nodesource.com/node_22.x\n'
            printf 'Suites: nodistro\n'
            printf 'Components: main\n'
            printf 'Architectures: %s\n' "$architecture"
            printf 'Signed-By: /usr/share/keyrings/nodesource.gpg\n'
        } > /etc/apt/sources.list.d/nodesource.sources
        chmod a+r /etc/apt/sources.list.d/nodesource.sources
        apt-get update
        apt-get install -y nodejs
    fi
    [[ "$(node --version)" == v22.* ]] || fail "Node.js 22 installation did not complete successfully."
    command -v npm >/dev/null 2>&1 || fail "The Node.js package did not provide npm."

    if ! command -v caddy >/dev/null 2>&1; then
        install -d -m 0755 /usr/share/keyrings
        curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/gpg.key | \
            gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
        curl -1sLf https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt > \
            /etc/apt/sources.list.d/caddy-stable.list
        chmod a+r /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
            /etc/apt/sources.list.d/caddy-stable.list
        apt-get update
        apt-get install -y caddy
    fi

    if ! odbcinst -q -d 2>/dev/null | grep -Fq '[ODBC Driver 18 for SQL Server]'; then
        local microsoft_package temporary_dir
        temporary_dir="$(mktemp -d)"
        microsoft_package="$temporary_dir/packages-microsoft-prod.deb"
        curl -fsSL "https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb" \
            -o "$microsoft_package"
        dpkg -i "$microsoft_package"
        rm -rf -- "$temporary_dir"
        apt-get update
        ACCEPT_EULA=Y apt-get install -y msodbcsql18
    fi

    if [[ "$(pnpm --version 2>/dev/null || true)" != "11.7.0" ]]; then
        npm install --global pnpm@11.7.0
    fi
}

ensure_identity_and_directories() {
    if ! id "$service_user" >/dev/null 2>&1; then
        adduser --system --group --home "$state_root" --no-create-home "$service_user"
    fi
    install -d -m 0755 -o root -g root "$install_root" "$install_root/releases"
    install -d -m 0750 -o root -g "$service_group" "$config_dir"
    install -d -m 0750 -o "$service_user" -g "$service_group" \
        "$state_root" "$state_root/users" "$state_root/update"
    install -d -m 0750 -o root -g "$service_group" \
        "$state_root/secrets" "$state_root/database"
    install -d -m 0750 -o caddy -g caddy /var/lib/caddy/data /var/lib/caddy/config
}

release_value() {
    local key="$1"
    local release_file="$project_root/deployment/release.env"
    [[ -r "$release_file" ]] || return 0
    (
        set -a
        # shellcheck disable=SC1090
        source "$release_file"
        printf '%s' "${!key:-}"
    )
}

derive_release() {
    app_version="$(release_value APP_VERSION)"
    app_repository="$(release_value APP_REPOSITORY)"
    if [[ -z "$app_version" ]] && command -v git >/dev/null 2>&1 && git -C "$project_root" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
        [[ -z "$(git -C "$project_root" status --porcelain --untracked-files=normal)" ]] || \
            fail "The source checkout has local changes. Commit or remove them before creating a VM release."
        app_version="git-$(git -C "$project_root" rev-parse --short=12 HEAD)"
    fi
    [[ "$app_version" =~ ^(v[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?|git-[a-f0-9]{7,40})$ ]] || \
        fail "Could not determine a safe release version. Use a tagged bundle or Git checkout."
    [[ -n "$app_repository" ]] || app_repository="https://github.com/csolomonson/Meziere-Cost-Calculator"
    release_dir="$install_root/releases/$app_version"
}

build_and_stage_release() {
    if [[ -d "$release_dir" ]]; then
        log "Reusing installed release $app_version"
        return
    fi

    log "Testing and building the browser application"
    (cd "$project_root" && pnpm install --frozen-lockfile && pnpm test && pnpm run build)
    [[ -s "$project_root/static/dist/app.js" ]] || fail "The production frontend bundle was not created."

    staging_dir="$install_root/releases/.staging-$app_version-$$"
    install -d -m 0755 -o root -g root "$staging_dir"
    local -a runtime_paths=(
        api.py app_config.py authentication.py cost_calculator.py requirements.txt
        update_contract.py user_management.py costing database deployment reporting
        repositories static tools utils web
    )
    tar -C "$project_root" -cf - "${runtime_paths[@]}" | tar -C "$staging_dir" -xf -

    python3 -m venv "$staging_dir/.venv"
    "$staging_dir/.venv/bin/python" -m pip install --upgrade pip
    "$staging_dir/.venv/bin/python" -m pip install --requirement "$staging_dir/requirements.txt"

    {
        printf 'APP_VERSION=%q\n' "$app_version"
        printf 'APP_REPOSITORY=%q\n' "$app_repository"
    } > "$staging_dir/deployment/release.env"
    chmod 0644 "$staging_dir/deployment/release.env"
    chown -R root:root "$staging_dir"
    mv -- "$staging_dir" "$release_dir"
    staging_dir=""
}

install_service_definitions() {
    install -m 0644 -o root -g root \
        "$release_dir/deployment/ubuntu/cost-calculator.service" \
        /etc/systemd/system/cost-calculator.service
    install -d -m 0755 -o root -g root /etc/systemd/system/caddy.service.d
    install -m 0644 -o root -g root \
        "$release_dir/deployment/ubuntu/caddy-override.conf" \
        /etc/systemd/system/caddy.service.d/cost-calculator.conf
    install -m 0644 -o root -g root "$release_dir/deployment/Caddyfile" /etc/caddy/Caddyfile
    systemctl daemon-reload
}

configure_release() {
    COST_APP_SOURCE_ROOT="$release_dir" \
    COST_APP_PYTHON="$release_dir/.venv/bin/python" \
    COST_APP_CONFIG_DIR="$config_dir" \
    COST_APP_STATE_ROOT="$state_root" \
        bash "$release_dir/deployment/ubuntu/configure.sh"
}

preflight_release() {
    log "Running database, user, and PDF preflight for $app_version"
    runuser -u "$service_user" -- bash -c '
        set -a
        source "$1"
        source "$2"
        set +a
        cd "$3"
        exec .venv/bin/python -m tools.deployment_preflight
    ' bash "$config_dir/runtime.env" "$release_dir/deployment/release.env" "$release_dir" || {
        printf '\nThe candidate release was not activated. For new storage, have a DBA review and run:\n  %s/database/reset-selected-storage.sql\n' "$state_root" >&2
        return 1
    }
}

activate_release() {
    local previous_release temporary_link
    previous_release="$(readlink -f "$install_root/current" || true)"
    temporary_link="$install_root/.current.$$"
    ln -s "$release_dir" "$temporary_link"
    mv -Tf -- "$temporary_link" "$install_root/current"
    install -m 0640 -o root -g "$service_group" \
        "$release_dir/deployment/release.env" "$config_dir/release.env"
    if [[ -n "$previous_release" && "$previous_release" != "$release_dir" ]]; then
        printf '%s\n' "$previous_release" > "$state_root/previous-release"
        chown root:root "$state_root/previous-release"
        chmod 0600 "$state_root/previous-release"
    fi
}

start_and_verify() {
    systemctl enable caddy.service cost-calculator.service
    systemctl restart cost-calculator.service
    systemctl restart caddy.service
    local attempt
    for attempt in {1..30}; do
        if systemctl is-active --quiet cost-calculator.service && \
            systemctl is-active --quiet caddy.service && \
            [[ -s /var/lib/caddy/data/caddy/pki/authorities/local/root.crt ]]; then
            if curl --fail --silent --max-time 2 http://127.0.0.1:8000/api/health >/dev/null 2>&1; then
                break
            fi
        fi
        sleep 1
    done
    bash "$release_dir/deployment/ubuntu/verify.sh"
}

require_host
install_host_packages
ensure_identity_and_directories
derive_release
build_and_stage_release
install_service_definitions
configure_release
preflight_release
activate_release
start_and_verify

log "Native VM deployment succeeded"
printf 'Release: %s\n' "$release_dir"
printf 'Rollback: sudo bash %s/deployment/ubuntu/rollback.sh\n' "$install_root/current"
