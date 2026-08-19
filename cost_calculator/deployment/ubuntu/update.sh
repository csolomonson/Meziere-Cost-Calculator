#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd -- "$script_dir/../.." && pwd)"

usage() {
    printf 'Usage: sudo bash deployment/ubuntu/update.sh\n'
    printf 'Extract the new GitHub release bundle over this deployment directory first.\n'
}

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    usage
    exit 0
fi
[[ "$#" -eq 0 ]] || {
    usage >&2
    exit 2
}
[[ "${EUID:-$(id -u)}" -eq 0 ]] || {
    printf 'Run with sudo: sudo bash deployment/ubuntu/update.sh\n' >&2
    exit 1
}
[[ -s "$project_root/deployment/release.env" ]] || {
    printf 'deployment/release.env is missing; extract a GitHub release bundle first.\n' >&2
    exit 1
}

exec bash "$script_dir/start.sh"
