# Ubuntu 22.04 and 24.04 native VM runbook

The application runs directly on an Ubuntu Server 22.04 or 24.04 LTS VM. Docker,
Compose, and a container registry are not used. On Ubuntu 22.04, the installer
adds the deadsnakes PPA for Python 3.11 because the OS default Python 3.10 cannot
run pandas 3. Ubuntu 24.04 uses its system Python 3.12.

## VM preparation

Start with at least 2 vCPU, 4 GB RAM, 30 GB disk, a fixed IPv4 address, and a
stable DNS name such as `cost-calculator.example.internal`.

| Direction | Port | Scope | Purpose |
| --- | ---: | --- | --- |
| Inbound | TCP 22 | administration network only | SSH management |
| Inbound | TCP 443 | approved client networks | application HTTPS |
| Outbound | SQL fixed TCP port | SQL Server only | ERP and costing data |
| Outbound | TCP 443 | package and GitHub endpoints | install and updates |
| Outbound | DNS/NTP | organization services | name resolution and time |

Use a fixed SQL Server endpoint in `host,port` form. Give the runtime SQL login
read access to the required ERP objects and DML access to the selected costing
schema. Do not give it database-creation or schema-owner privileges.

## Install from Git

Clone the reviewed branch into a deployment-owned checkout:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/cost-calculator-source
git clone https://github.com/csolomonson/Meziere-Cost-Calculator.git \
  /opt/cost-calculator-source
cd /opt/cost-calculator-source/cost_calculator
sudo bash deployment/ubuntu/install.sh
```

The first run asks for the application hostname and VM address, SQL endpoint and
login, costing database/schema, report company name, SQL password, and initial
application administrator. It installs Python, Node.js 22/pnpm, Microsoft ODBC
Driver 18, and Caddy from their signed package repositories. Later runs preserve
all existing configuration and secrets.

The installer creates a release from the checked-out Git commit. Tagged GitHub
release archives work the same way: verify the adjacent `.sha256`, extract the
archive into a new directory, and run its `deployment/ubuntu/install.sh`.

## Prepare a new costing schema

For a new or intentionally disposable costing store, the first installer run can
stop at preflight because tables do not exist yet. It prints this generated file:

```text
/var/lib/cost-calculator/database/reset-selected-storage.sql
```

Have a DBA review and execute that file with SSMS in SQLCMD mode or `sqlcmd -b`.
It is destructive for an existing target. Rerun the installer afterward; it will
reuse the staged release and finish activation.

If SQL Server uses a private CA, install only its PEM-encoded public root and
intermediate certificates, then rerun the installer:

```bash
sudo bash deployment/ubuntu/install-sql-ca.sh company-root.crt company-intermediate.crt
```

Never copy a private key to the VM.

## Validate and distribute client trust

The installer runs the same verifier available for routine checks:

```bash
sudo bash /opt/cost-calculator/current/deployment/ubuntu/verify.sh
sudo systemctl status cost-calculator caddy
sudo journalctl -u cost-calculator -u caddy --since today
```

The verifier checks both services, both SQL connections, the selected schema,
ReportLab, and HTTPS through the hostname and VM address. It exports Caddy's public
root certificate here:

```text
/var/lib/cost-calculator/caddy-root.crt
```

Distribute only that public certificate through managed client configuration.
Caddy's private CA material remains accessible only to the `caddy` account.

## Update

From the clean production checkout, fetch and fast-forward the reviewed branch,
stage it as a new release, preflight it, and activate it:

```bash
cd /opt/cost-calculator-source/cost_calculator
sudo bash deployment/ubuntu/update.sh
```

The production updater defaults to the native `no_docker` branch. To select a
different reviewed branch deliberately, provide its name explicitly:

```bash
cd /opt/cost-calculator-source/cost_calculator
sudo bash deployment/ubuntu/update.sh another-branch
```

## Application access groups

The shared user directory supports separate access to the co-hosted applications:

- `users` grants Product Cost Calculator access.
- `sales-orders` grants Shopify Sales Order Queue access.
- `administrators` grants both and permits user management.

Create a sales-order-only employee with only the `sales-orders` group. Add both
`users` and `sales-orders` when an employee needs both applications.

Verify a sales-order-only account against the costing boundary with:

```bash
curl --user employee-name -i https://costing.meziere.net/api/session
```

`curl` prompts for the password; the expected response is `HTTP 403`. Browsers
cache HTTP Basic credentials for a hostname, so use a fresh private window or a
separate browser profile when testing a different account. Seeing the costing
screen in a browser that was previously authenticated as an administrator does
not establish which credentials the browser is currently sending.

The update script refuses a dirty checkout and a non-fast-forward update. To
deploy an extracted tagged bundle instead, run that bundle's `install.sh`.

Routine updates preserve `/etc/cost-calculator/caddy.env`; they cannot silently
replace the hostname or IP address used for TLS. Before fetching code, the
updater also confirms that the runtime and Caddy hostnames and IP addresses
agree. If this safety check fails, it stops without changing files or restarting
services. Correct the configuration, or use the explicit reconfiguration
procedure below when a hostname or VM address change is intentional.

## Roll back

To switch back to the previously active application release:

```bash
sudo bash /opt/cost-calculator/current/deployment/ubuntu/rollback.sh
```

Rollback changes the `/opt/cost-calculator/current` symlink and restarts the app.
It does not reverse database migrations or modify users, passwords, Caddy state,
or SQL data.

## Reconfigure and backup

To deliberately replace runtime settings:

```bash
sudo bash /opt/cost-calculator/current/deployment/ubuntu/configure.sh --reconfigure
sudo systemctl restart cost-calculator caddy
sudo bash /opt/cost-calculator/current/deployment/ubuntu/verify.sh
```

Use `configure.sh --replace-db-password` for a SQL password rotation without
changing the non-secret runtime settings.

Back up SQL data using the organization's SQL Server backup system. Also protect
`/etc/cost-calculator`, `/var/lib/cost-calculator`, and `/var/lib/caddy/data` as
secret VM state. The last path preserves the CA already trusted by clients.
