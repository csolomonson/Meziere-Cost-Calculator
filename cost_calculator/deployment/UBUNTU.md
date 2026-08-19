# Ubuntu 22.04.5 container deployment

This runbook installs a published GitHub Release on Ubuntu Server 22.04.5. The
release image supports both amd64 and arm64. Use at least 2 vCPU, 4 GB RAM, and
30 GB of disk, with a static IPv4 address and stable DNS name.

## Network and database prerequisites

Allow the following traffic:

| Direction | Port | Scope | Purpose |
| --- | ---: | --- | --- |
| Inbound | TCP 22 | administration network only | SSH management |
| Inbound | TCP 443 | approved client networks | application HTTPS |
| Outbound | TCP 1433 or selected fixed port | SQL Server only | ERP and costing data |
| Outbound | TCP 443 | Docker, GitHub, GHCR | first install and updates |
| Outbound | UDP/TCP 53 | organization DNS | name resolution |
| Outbound | UDP 123 | organization NTP | time synchronization |

Docker-published ports may bypass some host firewall rules. Enforce the inbound
allowlist at the hypervisor, cloud security group, or upstream firewall too.

Configure SQL Server with a fixed `host,port` endpoint. Linux containers should
not use a Windows named instance such as `host\\instance`. The runtime SQL login
needs read access to required ERP objects and read/write access to the selected
costing schema. Use a separate privileged DBA account for schema setup.

## Download and verify the release

Set the version and download both release assets:

```bash
RELEASE_VERSION=v1.2.3
RELEASE_BASE="https://github.com/csolomonson/Meziere-Cost-Calculator/releases/download/$RELEASE_VERSION"
curl --fail --location --remote-name \
  "$RELEASE_BASE/cost-calculator-$RELEASE_VERSION-linux.tar.gz"
curl --fail --location --remote-name \
  "$RELEASE_BASE/cost-calculator-$RELEASE_VERSION-linux.tar.gz.sha256"
sha256sum --check "cost-calculator-$RELEASE_VERSION-linux.tar.gz.sha256"
```

Install the bundle into a fixed directory. Reusing this path on upgrades retains
the ignored `.env`, secrets, and runtime artifacts:

```bash
sudo install -d -m 0755 /opt/cost-calculator
sudo tar -xzf "cost-calculator-$RELEASE_VERSION-linux.tar.gz" \
  --strip-components=1 -C /opt/cost-calculator
cd /opt/cost-calculator
```

The archive contains no application source and no credentials. Its
`deployment/release.env` selects the release image by GHCR tag and SHA-256 digest.

If the GHCR package is private, authenticate before startup with a token having
only `read:packages` access:

```bash
printf '%s' "$GHCR_READ_TOKEN" | sudo docker login ghcr.io \
  --username YOUR_GITHUB_USER --password-stdin
unset GHCR_READ_TOKEN
```

## Optional SQL Server certificate authority

Production should validate the SQL Server certificate. If it uses an internal CA,
copy only the PEM-encoded public root and intermediate certificates before
startup:

```bash
sudo install -m 0644 company-sql-root.crt \
  /opt/cost-calculator/deployment/sql-ca/company-sql-root.crt
```

Never copy a SQL private key. Startup combines these public certificates with the
Ubuntu CA bundle and mounts the result read-only into the application container.

## Configure and start

Run one command:

```bash
cd /opt/cost-calculator
sudo bash deployment/ubuntu/start.sh
```

On the first run, the startup configuration prompts for:

- application DNS hostname and VM IPv4 address;
- SQL Server `host,port`, login, ERP database, and costing storage layout;
- whether SQL certificate identity validation is temporarily bypassed;
- the SQL password; and
- the initial application administrator username and password.

The script installs Docker Engine and Compose from Docker's official Ubuntu
repository if needed. It then pulls the digest-pinned application and Caddy
images, writes protected host configuration, and runs the deployment preflight in
a one-off application container. No compiler or application build tool is
installed on the server.

For a new database or disposable schema, the first preflight can stop because the
tables do not exist. Have a DBA review and run:

```text
/opt/cost-calculator/deployment/runtime/reset-selected-storage.sql
```

That generated script is destructive within the selected app schema. The runtime
login never executes it. After the DBA completes setup, rerun `start.sh`.

Successful startup prints the hostname and IPv4 URLs and exports Caddy's public
root certificate to:

```text
/opt/cost-calculator/deployment/runtime/caddy-root.crt
```

Distribute that public certificate through managed client configuration (for
example Group Policy or endpoint management). Do not distribute Caddy private
keys or Docker volume contents.

## Verify

Run the full automated verifier after installation and after every update:

```bash
sudo bash deployment/ubuntu/verify.sh
```

It checks the container state, SQL credentials, required schema, PDF runtime,
process health, database-aware readiness, and HTTPS at both configured addresses.

Also complete a browser smoke test: reject an invalid login, sign in as the
administrator, calculate and save a representative cost, reopen it, and open both
PDF reports.

## Upgrade

Download and checksum the new assets exactly as above. Extract the new bundle over
`/opt/cost-calculator`, then run:

```bash
cd /opt/cost-calculator
sudo bash deployment/ubuntu/update.sh
sudo bash deployment/ubuntu/verify.sh
```

The release metadata updates `.env` to the new digest. Startup preflight completes
before the running containers are replaced. The fixed Compose project name keeps
the application-user and Caddy volumes attached across versions.

## Rollback and operations

Rollback to the previously recorded application image without changing data:

```bash
sudo bash deployment/ubuntu/rollback.sh
sudo bash deployment/ubuntu/verify.sh
```

Useful diagnostics:

```bash
sudo docker compose ps
sudo docker compose logs --tail=200 app proxy
APP_CONTAINER="$(sudo docker compose ps -q app)"
sudo docker inspect --format '{{.Config.Image}} {{.State.Health.Status}}' "$APP_CONTAINER"
```

Restarting the VM is safe: Docker is enabled at boot and both services use
`restart: unless-stopped`. Back up the application-user and Caddy data volumes as
part of VM protection, and keep SQL data under the organization's SQL Server
backup policy.
