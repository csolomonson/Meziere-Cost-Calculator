# Ubuntu 22.04.5 single-image installation

The server needs Docker Engine, outbound HTTPS access to GHCR, a fixed IPv4
address, inbound TCP 443, and network access to SQL Server's fixed TCP port. The
application supports amd64 and arm64.

## 1. Select the release image

Use the version published on the GitHub Release page:

```bash
IMAGE="ghcr.io/csolomonson/meziere-cost-calculator:v1.2.3"
```

For a private GHCR package, log in with a classic token containing only
`read:packages`:

```bash
read -rsp "GHCR read token: " GHCR_READ_TOKEN
printf '\n'
printf '%s' "$GHCR_READ_TOKEN" | sudo docker login ghcr.io \
  --username YOUR_GITHUB_USERNAME --password-stdin
unset GHCR_READ_TOKEN
```

## 2. Configure the retained state

The volume is created automatically by the first command. Configuration is
interactive and remains available when the container is replaced:

```bash
sudo docker run --rm -it \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$IMAGE" configure
```

The command asks for the server hostname and IPv4 address, SQL endpoint and login,
database/schema selection, SQL password, report company, and initial application
administrator. It also runs the database and PDF preflight.

If SQL Server uses a private CA, install its PEM-encoded public root/intermediate
bundle, then rerun `configure` or `preflight`:

```bash
sudo docker run --rm -i \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$IMAGE" install-ca < company-sql-ca.crt
```

Never provide a SQL Server private key.

For new or disposable costing storage, export the generated DBA script:

```bash
sudo docker run --rm \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$IMAGE" database-setup > reset-selected-storage.sql
```

Have a DBA review and run it once, then confirm preflight:

```bash
sudo docker run --rm \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$IMAGE" preflight
```

## 3. Start the single container

```bash
sudo docker run -d \
  --name cost-calculator \
  --restart unless-stopped \
  --init \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --log-driver local \
  --log-opt max-size=10m \
  --log-opt max-file=5 \
  --publish 443:8443 \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$IMAGE"
```

The default command runs preflight and then starts Uvicorn plus Caddy. Docker's
health status is database-aware:

```bash
sudo docker ps
sudo docker inspect --format '{{.State.Health.Status}}' cost-calculator
sudo docker logs --tail=200 cost-calculator
```

Export Caddy's public root certificate after the first successful start:

```bash
sudo docker run --rm \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$IMAGE" export-ca > caddy-root.crt
```

Distribute only that public certificate through managed client configuration.

## Update

Pull and preflight the new version before replacing the container:

```bash
NEW_IMAGE="ghcr.io/csolomonson/meziere-cost-calculator:v1.2.4"
sudo docker pull "$NEW_IMAGE"
sudo docker run --rm \
  --mount type=volume,src=cost-calculator-data,dst=/var/lib/cost-calculator \
  "$NEW_IMAGE" preflight
```

Record the current image, then recreate the container with the same `docker run`
options shown above and `$NEW_IMAGE`:

```bash
sudo docker inspect --format '{{.Config.Image}}' cost-calculator
sudo docker stop cost-calculator
sudo docker rename cost-calculator cost-calculator-rollback
```

After the replacement passes health and browser checks, remove the stopped backup:

```bash
sudo docker rm cost-calculator-rollback
```

To roll back before removing it, stop and remove the replacement, rename the old
container to `cost-calculator`, and start it. The named volume and SQL databases
are not rolled back.

## Backup

Protect SQL data using the organization's SQL Server backup system. Back up the
`cost-calculator-data` Docker volume because it contains application users,
configuration, and Caddy's CA. Treat the backup as secret material.
