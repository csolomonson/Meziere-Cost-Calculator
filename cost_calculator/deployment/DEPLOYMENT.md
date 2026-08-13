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

For a new `.env`, the installer also asks whether app-owned costing tables should
use a dedicated database or a dedicated schema inside the ERP database. Existing
deployments default to their current dedicated database and `dbo` schema. The
selection is stored as:

```dotenv
COST_APP_STORAGE_MODE=database
COST_APP_DATABASE=M2_ME
COST_APP_SCHEMA=dbo
```

or, for an ERP namespace:

```dotenv
COST_APP_STORAGE_MODE=erp_schema
COST_APP_DATABASE=M1_ME
COST_APP_SCHEMA=CostCalculator
```

The installer generates `deployment/runtime/reset-selected-storage.sql` for a
database administrator to review and run. It never executes this destructive
script or grants the runtime login schema-administration privileges.

An existing rehearsal can replace its selection interactively with
`sudo bash deployment/ubuntu/install.sh --configure-storage`. This does not copy
or migrate costing data; the generated reset script is only for a new or
intentionally disposable target.

After the initial installation, update the application from `origin/master` with:

```bash
sudo bash deployment/ubuntu/update.sh
```

For a reviewed rehearsal branch, pass its name explicitly:

```bash
sudo bash deployment/ubuntu/update.sh codex
```

The updater refuses a dirty checkout or a non-fast-forward branch, fetches Git as
the account that invoked `sudo`, derives an immutable `git-<commit>` image version,
then runs both the installer and verifier. Database settings and secrets are not
changed.

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
- App-owned SQL is fully schema-qualified. In ERP-schema mode, the runtime login
  can be granted writes only to the dedicated app schema while retaining limited
  read access to required ERP objects.
- Caddy issues the site certificate from a deployment-local CA. The installer
  exports the public root for controlled distribution to clients.
- Application users and Caddy state live in named volumes and survive upgrades.

`GET /api/health` is a process liveness check. `GET /api/ready` verifies both the
ERP and costing database connections; Compose uses readiness, so a disconnected
application cannot be reported healthy.

## Releases and rollback

`update.sh` generates a matching `APP_VERSION` and `COST_APP_IMAGE` from the first
12 characters of the selected Git commit. Direct installer use must instead set a
unique matching version and image tag in `.env`. Once an image exists, the
installer treats it as immutable and will not rebuild the same tag. A successful
upgrade retains the previous image name in `deployment/runtime/previous-image`.

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
