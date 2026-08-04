# Ubuntu VM deployment runbook - August 17, 2026

This runbook is designed so the person assisting on deployment day only needs to
approve the final network change, run one command, and complete a short browser
smoke test. Do not leave VM creation, SQL networking, certificates, or schema
creation for August 17.

## Target architecture

Start with an Ubuntu Server 24.04 LTS VM with 2 vCPU, 4 GB RAM, and 30 GB of disk.
Increase resources if rehearsal data shows sustained CPU, memory, or storage
pressure. Use a static IP and a stable DNS name such as
`cost-calculator.example.internal`.

The VM needs:

| Direction | Port | Scope | Purpose |
| --- | ---: | --- | --- |
| Inbound | TCP 22 | administration network only | SSH management |
| Inbound | TCP 443 | approved client networks | application HTTPS |
| Outbound | TCP 1433 (or selected fixed port) | SQL Server only | ERP and costing databases |
| Outbound | UDP/TCP 53 | organization DNS | name resolution |
| Outbound | UDP 123 | organization NTP | time synchronization |
| Outbound during preparation | TCP 443 | approved package registries | Docker, base images, Python, Node, and Microsoft ODBC packages |

Docker-published ports can bypass some host firewall rules, so enforce the inbound
allowlist at the hypervisor, cloud security group, or upstream firewall as well as
on the VM. Compose publishes only 443.

Use a fixed SQL Server TCP endpoint in `host,port` form. Linux containers should
not depend on Windows named-instance discovery. The runtime SQL login should have
read access to the ERP database and read/write access to the costing database; use
a separate privileged account for schema setup.

## Hyper-V rehearsal quick start (Ubuntu 22.04.5)

Ubuntu 22.04.5 is supported by the installer. For a VM attached to Hyper-V's
Default Switch, the guest's default gateway is normally the Windows host endpoint
that the container can use to reach SQL Server. Confirm it rather than hard-coding
an address because the Default Switch subnet can change.

On the Ubuntu VM:

```bash
WINDOWS_HOST_IP="$(ip route show default | awk '/default/ {print $3; exit}')"
VM_IP="$(hostname -I | awk '{print $1}')"
printf 'Windows host: %s\nUbuntu VM: %s\n' "$WINDOWS_HOST_IP" "$VM_IP"

sudo apt-get update
sudo apt-get install -y git netcat-openbsd
nc -vz "$WINDOWS_HOST_IP" 1433
```

If the port test fails, use SQL Server Configuration Manager on Windows to enable
TCP/IP for the test instance, clear `TCP Dynamic Ports`, set `TCP Port` under
`IPAll` to a fixed port such as `1433`, and restart that SQL Server service. Then,
from an elevated Windows PowerShell session, allow only the rehearsal VM to reach
that port (replace the value with the `VM_IP` printed above):

```powershell
$VmIp = "172.20.0.10"
New-NetFirewallRule -DisplayName "Cost Calculator rehearsal SQL" `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 1433 `
  -RemoteAddress $VmIp
```

Repeat the `nc` test before continuing. Do not use `host\\instance`; the deployment
expects the fixed endpoint printed above as `$WINDOWS_HOST_IP,1433`.

Clone and deploy the rehearsal branch:

```bash
sudo install -d -o "$USER" -g "$USER" /opt/cost-calculator
git clone --branch codex --single-branch \
  https://github.com/csolomonson/Meziere-Cost-Calculator.git \
  /opt/cost-calculator
cd /opt/cost-calculator/cost_calculator
sudo bash deployment/ubuntu/install.sh
sudo bash deployment/ubuntu/verify.sh
```

For the first-run prompts, use `cost-calculator.test` as the application hostname,
`<WINDOWS_HOST_IP>,1433` as the SQL endpoint, and the test SQL login/database
names. It is acceptable to answer `y` to the SQL certificate bypass prompt only
for this isolated rehearsal; production should validate the SQL Server certificate.

After the installer succeeds, print the guest IP and export the Caddy root CA:

```bash
hostname -I
ls -l deployment/runtime/caddy-root.crt
```

On Windows, add `<VM_IP> cost-calculator.test` to the hosts file, copy
`deployment/runtime/caddy-root.crt` from the VM, and import only that known
rehearsal CA into `Cert:\LocalMachine\Root` from an elevated PowerShell session.
The application is then available at `https://cost-calculator.test/`. Remove the
firewall rule, hosts entry, and rehearsal CA when the VM is retired.

## Decisions to freeze by August 7

Record these values in the change ticket:

- VM hostname, static IP, and application DNS name;
- SQL Server DNS name and fixed TCP port;
- ERP and costing database names;
- runtime SQL login name;
- whether the SQL certificate chains to a public/system CA or an internal CA;
- initial application administrator username;
- release version and source commit; and
- client networks and people performing the smoke test.

Do not put either password in the ticket or `.env`.

## Complete by August 10

1. Provision and patch the Ubuntu 24.04 VM. Configure DNS, NTP, SSH keys, VM
   backups/snapshots, monitoring, and the upstream firewall.
2. Configure SQL Server with a fixed TCP port and allow the VM's IP. Confirm the
   SQL certificate name matches the DNS name used by the application.
3. Because the current costing data is disposable, use a database administration
   account to run `database/reset_schema.sql` once against the intended costing
   database. The script is destructive and currently contains `USE [M2_ME]`; if a
   different database name is selected, have the database owner review that line
   before execution. Never grant this schema privilege to the runtime login.
4. Grant the runtime login read access to the ERP database and read/write access
   to the newly created costing tables.
5. Copy a reviewed release directory to `/opt/cost-calculator`. Keep it owned by
   root or a dedicated deployment account and do not share-write it with the app.
6. If SQL Server uses an internal CA, copy only the public root/intermediate PEM
   certificates to `deployment/sql-ca/*.crt`. Never copy a private key.
7. From the release directory, run:

   ```bash
   sudo bash deployment/ubuntu/install.sh
   ```

   On the first run, the installer prompts for missing non-secret values, the SQL
   password, and an initial application administrator. Password input is hidden.
8. Import `deployment/runtime/caddy-root.crt` into the managed trust store for all
   client machines, preferably through Group Policy or the organization's endpoint
   management system. Do not send it as an arbitrary end-user download.
9. Run `sudo bash deployment/ubuntu/verify.sh`.

## Rehearsal - complete by August 12

Rehearse on the final VM or an exact clone with the same network rules:

1. Run the installer from a clean checkout and time it.
2. Confirm both database checks and all seven required costing tables pass.
3. From a managed client, verify HTTPS is trusted and matches the DNS name.
4. Verify a missing or incorrect login returns 401, then sign in as administrator.
5. Search for a part, calculate a representative cost, save it as current, reopen
   it, and confirm the saved user identity.
6. Open the PDF and compare its identity, totals, materials, operations, notes, and
   page numbers with the saved worksheet. Include a multi-page example.
7. Add a temporary user, reset its password, and remove it.
8. Restart the VM. Confirm Docker starts the application and rerun `verify.sh`.
9. Exercise `rollback.sh` with two harmless version tags, then redeploy the final
   tag. Schema changes are intentionally outside image rollback.
10. Save the results in the change record and resolve every warning.

Keep the final versioned image on the VM. The installer will not rebuild an
existing image tag, so the August 17 run needs no package or image downloads. If
code changes after rehearsal, assign a new version and repeat the rehearsal.

## Freeze - August 13 through August 16

- Freeze the source commit, version, image tag, `.env`, firewall change, DNS record,
  SQL permissions, and client trust deployment.
- Confirm `sudo docker image inspect <image-tag>` and
  `sudo docker image inspect caddy:2.11.4-alpine` both succeed on the VM.
- Confirm `.env` is mode 600. Confirm both files under `secrets/` are mode 400
  and owned by the UID/GID reported by the application image. Do not copy their
  contents into the ticket.
- Take a VM snapshot or confirm the VM backup restore point.
- Put the previous image tag and rollback command in the change record.
- Schedule the app owner, VM/network owner, SQL owner, and a business tester. The
  SQL owner should be on call, not doing routine installer work.

## August 17 execution

### 1. Start the change window

Confirm the frozen version, VM snapshot, SQL availability, DNS, client trust, and
inbound 443 rule. Stop if any frozen input differs from rehearsal.

### 2. Deploy

SSH to the VM, enter the release directory, and run exactly:

```bash
sudo bash deployment/ubuntu/install.sh
```

With the VM prepared, this command is non-interactive. It validates configuration,
SQL credentials, both databases, the schema, and ReportLab; starts the containers;
waits for readiness; checks HTTPS; and prints the running image. If it exits
nonzero, save the printed logs and use the rollback section instead of improvising
a partial fix.

### 3. Automated verification

```bash
sudo bash deployment/ubuntu/verify.sh
```

This must print `All automated deployment checks passed.`

### 4. Five-minute business smoke test

From a managed client using the production DNS name:

1. confirm HTTPS is trusted with no certificate warning;
2. confirm a bad password is rejected;
3. sign in and search for a known part;
4. calculate, save, reopen, and verify one representative costing run; and
5. select **Open PDF** and compare the unit and total costs.

Record the version from `/api/version`, the tester, and the pass time. The change
owner can then announce service availability.

## Rollback

If an upgrade fails and a previous version exists:

```bash
sudo bash deployment/ubuntu/rollback.sh
sudo bash deployment/ubuntu/verify.sh
```

This switches only the application image. It preserves users, Caddy state, and
database data, and it does not reverse database changes.

For a failed first deployment with no previous image:

```bash
sudo docker compose down
```

Leave named volumes in place for diagnosis. Do not add `--volumes`. Close or revert
inbound 443, document the failure, and reschedule after a complete rehearsal.

## Routine operations

```bash
sudo docker compose ps
sudo docker compose logs --tail=200 app proxy
sudo bash deployment/ubuntu/verify.sh
```

Future costing data must use the organization's SQL Server backup process. Also
back up the `user_data` and `caddy_data` Docker volumes before VM replacement; the
latter preserves the CA already trusted by clients.

The Docker installation follows the official guidance:

- <https://docs.docker.com/engine/install/ubuntu/>
- <https://docs.docker.com/compose/install/linux/>
