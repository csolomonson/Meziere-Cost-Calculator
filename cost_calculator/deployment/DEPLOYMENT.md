# Container release deployment

Production releases are immutable, multi-platform application images published to
GitHub Container Registry (GHCR). Each matching GitHub Release contains a small,
source-free Ubuntu deployment bundle. The server does not clone the repository,
install Python or Node.js, or build an image.

The bundle contains Compose, Caddy configuration, the Ubuntu scripts, the DBA
schema template, and `deployment/release.env`. The release workflow writes the
exact image tag and multi-platform digest into `release.env`; startup copies that
identity into the retained `.env` file. Pinning by digest prevents a moved tag from
silently changing the deployed application.

## Publish a release

Create and push a semantic version tag from the commit to release:

```bash
git tag -a v1.2.3 -m "v1.2.3"
git push origin v1.2.3
```

The repository-root `Publish container release` workflow then:

1. builds `linux/amd64` and `linux/arm64` images;
2. publishes `ghcr.io/<owner>/<repository>:v1.2.3`;
3. creates a GitHub artifact attestation for the image digest;
4. assembles `cost-calculator-v1.2.3-linux.tar.gz` without application source; and
5. creates the GitHub Release with the bundle and its SHA-256 checksum.

GHCR packages inherit repository access by default. For an unauthenticated
production pull, make the package public. For a private package, log in on the
server with a read-only classic personal access token before startup:

```bash
printf '%s' "$GHCR_READ_TOKEN" | sudo docker login ghcr.io \
  --username YOUR_GITHUB_USER --password-stdin
unset GHCR_READ_TOKEN
```

## Server lifecycle

Use [`UBUNTU.md`](UBUNTU.md) for the complete Ubuntu 22.04.5 procedure. The normal
entry point is:

```bash
sudo bash deployment/ubuntu/start.sh
```

`start.sh` runs `configure.sh` first. Configuration is idempotent and performs the
same important work as the former source-checkout installer: it installs Docker
when needed, creates or validates `.env` and secret files, builds the runtime CA
bundle, pulls the release image, creates the initial administrator, renders the
DBA setup script, and runs the database/PDF preflight in a one-off container. It
then starts the application and Caddy containers and verifies HTTPS readiness.
Inside the application container, `configure-container.sh` verifies the mounted
secrets and initializes the persistent application-user file before Uvicorn starts.

`install.sh` remains as a compatibility alias for `start.sh`. To rerun only the
configuration phase, use:

```bash
sudo bash deployment/ubuntu/configure.sh
```

After a successful configuration-only run, start without repeating it:

```bash
sudo bash deployment/ubuntu/start.sh --skip-configure
```

## Persistent and security boundaries

- The application image is pulled from GHCR by tag and digest; Compose has no
  server-side `build` section.
- Compose uses the fixed project name `cost-calculator`, so Caddy state,
  application users, and update state survive release-directory changes.
- SQL and application passwords remain file-backed secrets on the host and are
  never placed in the image, release bundle, or `.env`.
- Optional public SQL Server CA certificates in `deployment/sql-ca/*.crt` are
  appended to the Ubuntu trust bundle at startup and mounted read-only into the
  application. Site-specific trust material is not baked into the release image.
- Only Caddy publishes a host port (TCP 443). The application remains on the
  private Compose network.
- Both containers have read-only root filesystems, drop capabilities, and set
  `no-new-privileges`; Caddy receives only `NET_BIND_SERVICE`.
- The application has no Docker socket, host update credential, or GitHub token.

## Update and rollback

Download and verify a new release bundle, then extract it over the existing fixed
deployment directory. Keep `.env`, `secrets/`, and `deployment/runtime/`; they are
not present in the archive and are retained. Run:

```bash
sudo bash deployment/ubuntu/update.sh
```

This selects the new digest, runs startup configuration and preflight, records the
previous image, and replaces the containers without deleting volumes.

Roll back only the application image with:

```bash
sudo bash deployment/ubuntu/rollback.sh
```

Rollback does not alter named volumes or databases. Database migrations require a
separate reviewed rollback or restore plan.

`GET /api/health` is process liveness. `GET /api/ready` checks both SQL databases;
Compose waits on readiness before reporting startup success.
