# Native Ubuntu VM deployment

Production runs directly on an Ubuntu Server 24.04 LTS VM. Uvicorn runs as the
unprivileged `cost-calculator` system account and listens only on
`127.0.0.1:8000`. Caddy is a separate host service and is the only process that
accepts client traffic, on HTTPS port 443.

The one-command installer is:

```bash
sudo bash deployment/ubuntu/install.sh
```

It installs host prerequisites, builds the frontend, creates a versioned Python
virtual environment under `/opt/cost-calculator/releases`, collects configuration
and secrets on the first run, runs database and PDF preflight checks, atomically
selects the release, and enables both services. See
[`UBUNTU.md`](UBUNTU.md) for VM preparation and operational procedures.

## Filesystem and service boundaries

| Path | Owner and purpose |
| --- | --- |
| `/opt/cost-calculator/releases/<version>` | Root-owned immutable application release and virtual environment |
| `/opt/cost-calculator/current` | Symlink to the active release |
| `/etc/cost-calculator/runtime.env` | Root-owned runtime configuration, readable by the app group |
| `/etc/cost-calculator/caddy.env` | Hostname and IP only, readable by the Caddy service |
| `/etc/cost-calculator/release.env` | Active version and repository identity |
| `/var/lib/cost-calculator/secrets` | SQL password, outside every release |
| `/var/lib/cost-calculator/users` | Application user directory, writable only by the app service |
| `/var/lib/cost-calculator/database` | Generated DBA setup script |
| `/var/lib/caddy/data` | Caddy certificates and private local CA state |

`cost-calculator.service` uses systemd sandboxing, has no Linux capabilities, and
can write only its user and update-state directories. Caddy has a different Unix
identity, so the application cannot read Caddy's private CA key. SQL secrets and
application users survive releases and rollbacks.

## Releases

Push a semantic version tag:

```bash
git tag -a v1.2.5 -m "v1.2.5"
git push origin refs/tags/v1.2.5
```

The `Publish native VM release` workflow runs backend, frontend, and deployment
contract tests; builds the browser assets; and publishes an attested
`cost-calculator-<version>-ubuntu-vm.tar.gz` plus its SHA-256 file on the GitHub
Release. It does not publish a container image.

A release is tested before the `current` symlink changes. The previous release
path is retained in `/var/lib/cost-calculator/previous-release`, allowing an
application-only rollback without changing configuration, users, or SQL data.

## Update boundary

The web update endpoint remains a request/status contract; it cannot run commands
as root or modify the installed release. Operators deploy a reviewed bundle or use
`deployment/ubuntu/update.sh` from a clean Git checkout during a maintenance
window. Database migrations remain a separate DBA-reviewed operation.
