#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"
branch="${1:-no_docker}"

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

usage() {
    printf 'Usage: sudo bash deployment/ubuntu/update.sh [branch]\n'
    printf 'The default production branch is no_docker.\n'
}

if [[ "$branch" == "--help" || "$branch" == "-h" ]]; then
    usage
    exit 0
fi
[[ "$#" -le 1 ]] || {
    usage >&2
    exit 2
}
[[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/update.sh [branch]"
command -v git >/dev/null 2>&1 || fail "Git is required to update this checkout."
git check-ref-format --branch "$branch" >/dev/null 2>&1 || fail "Invalid Git branch name: $branch"

runtime_config="/etc/cost-calculator/runtime.env"
caddy_config="/etc/cost-calculator/caddy.env"
if [[ -s "$runtime_config" && -s "$caddy_config" ]]; then
    runtime_hostname="$(bash -c 'source "$1"; printf "%s" "${APP_HOSTNAME:-}"' bash "$runtime_config")"
    runtime_ip_address="$(bash -c 'source "$1"; printf "%s" "${APP_IP_ADDRESS:-}"' bash "$runtime_config")"
    caddy_hostname="$(bash -c 'source "$1"; printf "%s" "${APP_HOSTNAME:-}"' bash "$caddy_config")"
    caddy_ip_address="$(bash -c 'source "$1"; printf "%s" "${APP_IP_ADDRESS:-}"' bash "$caddy_config")"
    [[ -n "$runtime_hostname" && -n "$runtime_ip_address" && \
        "$runtime_hostname" == "$caddy_hostname" && "$runtime_ip_address" == "$caddy_ip_address" ]] || \
        fail "TLS safety check failed: runtime.env uses '$runtime_hostname' at '$runtime_ip_address' but caddy.env uses '$caddy_hostname' at '$caddy_ip_address'. No files or services were changed. Correct the configuration or deliberately run configure.sh --reconfigure before updating."
fi

git_user="${SUDO_USER:-}"
if [[ -z "$git_user" || "$git_user" == "root" ]]; then
    git_user="$(stat -c '%U' "$project_root")"
fi
[[ -n "$git_user" && "$git_user" != "UNKNOWN" ]] || fail "Could not determine the checkout owner."

run_git() {
    if [[ "$git_user" == "root" ]]; then
        git -C "$project_root" "$@"
    else
        sudo -H -u "$git_user" -- git -C "$project_root" "$@"
    fi
}

run_git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fail "$project_root is not a Git checkout."
[[ -z "$(run_git status --porcelain --untracked-files=normal)" ]] || fail "The checkout has local changes; refusing to update it."

printf '\n==> Fetching origin/%s as %s\n' "$branch" "$git_user"
run_git fetch --prune origin "+refs/heads/$branch:refs/remotes/origin/$branch"
run_git show-ref --verify --quiet "refs/remotes/origin/$branch" || fail "origin/$branch was not found."
project_prefix="$(run_git rev-parse --show-prefix)"
for required_path in deployment/ubuntu/install.sh deployment/ubuntu/verify.sh deployment/ubuntu/cost-calculator.service; do
    run_git cat-file -e "refs/remotes/origin/$branch:${project_prefix}${required_path}" 2>/dev/null || \
        fail "origin/$branch does not contain the native Ubuntu deployment."
done

if run_git show-ref --verify --quiet "refs/heads/$branch"; then
    run_git switch "$branch"
    run_git merge --ff-only "refs/remotes/origin/$branch"
else
    run_git switch --no-track -c "$branch" "refs/remotes/origin/$branch"
fi
[[ "$(run_git rev-parse HEAD)" == "$(run_git rev-parse refs/remotes/origin/$branch)" ]] || \
    fail "The local branch diverges from origin/$branch."

exec bash "$project_root/deployment/ubuntu/install.sh"
