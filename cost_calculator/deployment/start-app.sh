#!/usr/bin/env bash
set -Eeuo pipefail

/app/deployment/configure-container.sh

log() {
    printf '\n==> %s\n' "$*"
}

stop_services() {
    set +e
    [[ -z "${app_pid:-}" ]] || kill -TERM "$app_pid" 2>/dev/null
    [[ -z "${caddy_pid:-}" ]] || kill -TERM "$caddy_pid" 2>/dev/null
    [[ -z "${app_pid:-}" ]] || wait "$app_pid" 2>/dev/null
    [[ -z "${caddy_pid:-}" ]] || wait "$caddy_pid" 2>/dev/null
}

handle_signal() {
    trap - TERM INT
    stop_services
    exit 0
}
trap handle_signal TERM INT

log "Running database, user, and PDF preflight"
python -m tools.deployment_preflight

log "Starting Uvicorn on the container loopback interface"
uvicorn api:app \
    --host 127.0.0.1 \
    --port 8000 \
    --workers 2 \
    --proxy-headers \
    --forwarded-allow-ips="127.0.0.1" &
app_pid=$!

log "Starting Caddy HTTPS on container port 8443"
caddy run --config /app/deployment/Caddyfile --adapter caddyfile &
caddy_pid=$!

while kill -0 "$app_pid" 2>/dev/null && kill -0 "$caddy_pid" 2>/dev/null; do
    sleep 1
done

set +e
if ! kill -0 "$app_pid" 2>/dev/null; then
    wait "$app_pid"
    exit_status=$?
    printf 'Uvicorn stopped with status %s; stopping Caddy.\n' "$exit_status" >&2
else
    wait "$caddy_pid"
    exit_status=$?
    printf 'Caddy stopped with status %s; stopping Uvicorn.\n' "$exit_status" >&2
fi
stop_services
exit "$exit_status"
