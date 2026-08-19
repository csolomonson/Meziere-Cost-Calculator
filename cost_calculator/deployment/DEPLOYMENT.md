# Single-image container deployment

Each release is one multi-platform image in GitHub Container Registry. The image
contains the Python application, compiled React frontend, Microsoft SQL Server
ODBC driver, Caddy, configuration command, database preflight, and HTTPS runtime.
No source checkout, Compose file, deployment archive, Python installation, or
Node.js installation is required on the server.

The only host prerequisite is Docker Engine. Runtime configuration, SQL password,
application users, generated DBA script, update state, and Caddy PKI are retained
in the `cost-calculator-data` Docker volume. They are never baked into the image.

## Publish

Push a semantic tag beginning with `v`:

```bash
git tag -a v1.2.3 -m "v1.2.3"
git push origin refs/tags/v1.2.3
```

The `Publish container release` workflow tests the deployment contract and
frontend, builds `linux/amd64` and `linux/arm64`, publishes the image to GHCR,
attests its digest, and creates a GitHub Release. The release contains a small text
asset with the immutable `tag@sha256:digest` image reference; the image itself is
stored in GHCR.

## Image commands

The image entrypoint provides these commands:

| Command | Purpose |
| --- | --- |
| `configure` | Interactively create or update configuration, secrets, users, CA bundle, and DBA SQL in the named volume |
| `serve` | Run preflight, Uvicorn, and Caddy; this is the default |
| `preflight` | Verify users, both SQL connections, schema, and PDF runtime without starting services |
| `database-setup` | Write the generated destructive DBA setup SQL to standard output |
| `install-ca [FILE]` | Add a public internal SQL Server CA certificate to the retained trust bundle; also accepts PEM on standard input |
| `export-ca` | Write Caddy's public local root certificate to standard output after the application has started once |

See [`UBUNTU.md`](UBUNTU.md) for exact Docker commands.

## Security and persistence

- The container runs as fixed UID/GID 10001 with a read-only root filesystem,
  every capability dropped, `no-new-privileges`, and only `/tmp` plus the named
  state volume writable.
- Caddy listens on unprivileged container port 8443; Docker publishes host port
  443. Uvicorn listens only on container loopback port 8000.
- The SQL password and application password hashes exist only in the named volume.
- Image updates and rollbacks reuse the same state volume and do not change SQL
  data.
- Caddy's internal CA persists in the named volume, so clients do not need a new
  trust certificate after image replacement.

Bundling Caddy deliberately trades away the former process and credential
isolation between two containers. Caddy and the application now share a container
identity and state volume, so an application-container compromise could reach
Caddy's private CA material. This is the primary cost of the single-image design.

Do not mount the Docker socket, place secrets in image build arguments, or publish
the state volume. Anyone with root or Docker access on the server can read the
volume and should be treated as a deployment administrator.
