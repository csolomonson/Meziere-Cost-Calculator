# Production deployment

The supported production target is an Ubuntu Server 24.04 LTS VM running Docker
Engine and Docker Compose. Caddy is the only published service and exposes HTTPS
on TCP 443. The FastAPI container is reachable only from the private Compose
network.

For the exact preparation and August 17, 2026 procedure, use
[`UBUNTU.md`](UBUNTU.md). The day-of deployment command is:

```bash
sudo bash deployment/ubuntu/install.sh
```

The installer is idempotent and fail-fast. It installs Docker from Docker's
official Ubuntu repository when needed, creates missing configuration and secrets
interactively, builds a versioned image once, validates both SQL databases and the
costing schema, starts the containers, waits for database-aware readiness, verifies
HTTPS, and exports the Caddy root certificate.

## Security boundaries

- Only TCP 443 is published by Compose. Port 8000 is never bound to the VM.
- Both containers use a read-only root filesystem, drop Linux capabilities, and
  set `no-new-privileges`; Caddy receives only `NET_BIND_SERVICE`.
- Database and application passwords are mounted as files, excluded from Git, and
  not baked into images.
- The application has no Docker socket, host filesystem, SSH key, or update
  credential.
- SQL Server uses encrypted ODBC connections. A private CA can be staged under
  `deployment/sql-ca/` rather than disabling certificate validation.
- Caddy issues the site certificate from a deployment-local CA. The installer
  exports the public root for controlled distribution to clients.
- Application users and Caddy state live in named volumes and survive upgrades.

`GET /api/health` is a process liveness check. `GET /api/ready` verifies both the
ERP and costing database connections; Compose uses readiness, so a disconnected
application cannot be reported healthy.

## Releases and rollback

Set a unique `APP_VERSION` and matching `COST_APP_IMAGE` tag for every build. Once
that image exists, the installer treats it as immutable and will not rebuild the
same tag. A successful upgrade retains the previous image name in
`deployment/runtime/previous-image`.

Rollback only the application containers with:

```bash
sudo bash deployment/ubuntu/rollback.sh
```

This does not modify Docker volumes or databases. Database schema changes need a
separate, tested rollback or restore. For the first deployment, where no prior
image exists, take the site out of service with `sudo docker compose down`; named
volumes remain available.

## Update UI boundary

The existing update endpoints are a request/status contract only. The web
application deliberately cannot install host updates. Do not give it the Docker
socket. Until a separate signed-release supervisor is implemented, upgrades are
performed from a reviewed release directory with the installer above.

The retired Windows/IIS scripts are preserved for historical reference in
`deployment/windows`, but they are not a supported production path and are
excluded from the container build.
