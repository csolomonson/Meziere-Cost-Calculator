#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
    printf 'ERROR: %s\n' "$*" >&2
    exit 1
}

[[ "${EUID:-$(id -u)}" -eq 0 ]] || fail "Run with sudo: sudo bash deployment/ubuntu/install-sql-ca.sh CERTIFICATE.crt [...]"
[[ "$#" -ge 1 ]] || fail "Provide one or more PEM-encoded public CA certificate files."
command -v update-ca-certificates >/dev/null 2>&1 || fail "update-ca-certificates is not installed."

for certificate in "$@"; do
    [[ -r "$certificate" ]] || fail "Cannot read CA certificate: $certificate"
    grep -q -- '-----BEGIN CERTIFICATE-----' "$certificate" || fail "Not a PEM certificate: $certificate"
done

rm -f -- /usr/local/share/ca-certificates/cost-calculator-sql-*.crt
index=0
for certificate in "$@"; do
    index=$((index + 1))
    install -m 0644 -o root -g root "$certificate" "/usr/local/share/ca-certificates/cost-calculator-sql-$index.crt"
done
update-ca-certificates --fresh
printf 'Installed %s public SQL Server CA certificate(s).\n' "$index"
systemctl try-restart cost-calculator.service
printf 'Rerun the native installer or verifier to confirm SQL certificate trust.\n'
