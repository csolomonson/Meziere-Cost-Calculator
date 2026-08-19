#!/usr/bin/env bash
set -Eeuo pipefail

install_root="/opt/cost-calculator"
config_dir="/etc/cost-calculator"
state_root="/var/lib/cost-calculator"
previous_file="$state_root/previous-release"

fail() {
    printf '\nERROR: %s\n' "$*" >&2
    exit 1
}

[[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/rollback.sh"
[[ -s "$previous_file" ]] || fail "No previous native release was recorded."
previous_release="$(tr -d '\r\n' < "$previous_file")"
case "$previous_release" in
    "$install_root"/releases/*) ;;
    *) fail "Refusing unexpected rollback path: $previous_release" ;;
esac
[[ -d "$previous_release" && -r "$previous_release/deployment/release.env" ]] || \
    fail "The previous release is no longer available: $previous_release"

current_release="$(readlink -f "$install_root/current" || true)"
temporary_link="$install_root/.current.rollback.$$"
ln -s "$previous_release" "$temporary_link"
mv -Tf -- "$temporary_link" "$install_root/current"
install -m 0640 -o root -g cost-calculator \
    "$previous_release/deployment/release.env" "$config_dir/release.env"
if [[ -n "$current_release" && "$current_release" != "$previous_release" ]]; then
    printf '%s\n' "$current_release" > "$previous_file"
    chmod 0600 "$previous_file"
fi
systemctl restart cost-calculator.service
systemctl reload caddy.service
bash "$install_root/current/deployment/ubuntu/verify.sh"
printf 'Rollback completed: %s\n' "$previous_release"
