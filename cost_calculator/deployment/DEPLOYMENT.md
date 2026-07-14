# Production deployment design

## What is implemented

- Every page and API route except the process health probe requires a user and password.
- Successful password verification is cached as a keyed in-memory digest for five minutes, avoiding an expensive password hash on every API request. Changing the configured password hash invalidates the cache immediately.
- The authenticated username is written to `PartCosts.ucpCostedBy`; client-supplied values are ignored.
- User records can already contain `groups`, providing the identity shape needed for later authorization rules.
- Administrators can add, delete, re-group, and reset passwords from the home screen. The initial secret seeds a persistent writable user volume on first start; subsequent changes remain in that volume.
- Database and login secrets come from mounted files and are excluded from the image and repository.
- The browser application is compiled into the image. A running installation does not contact a CDN.
- Caddy provides HTTPS in front of the application with a locally issued certificate.
- `/api/version` reports the immutable deployed version and source repository supplied at build/deploy time.
- `/api/update` and `/api/update/install` provide a file-based contract with a separate supervisor. Only users in the `administrators` group can request installation.

## Updates: use a separate, least-privileged supervisor

The web application must not receive access to the Docker socket, repository write credentials, or permission to replace its own executable. A compromise of an ordinary app login would otherwise become control of the deployment host.

Use this release flow:

1. CI builds a versioned image from a Git tag, runs tests, and publishes an image plus its SHA-256 digest. Export the image as an OCI archive for sites that may be offline.
2. A small host-level update supervisor polls the GitHub Releases API using a read-only token. It writes `update-status.json` into the `update_state` volume consumed by the app. Network failure means `status: offline`, not an application failure.
3. When an administrator selects **Install update**, the app atomically writes `update-request.json` into that volume. The supervisor downloads the immutable image and verifies the expected digest (and, preferably, a Sigstore signature).
4. The supervisor starts the candidate beside the current container, waits for process and database readiness checks, then changes the reverse-proxy upstream. Existing requests drain before the old container stops.
5. If readiness fails, traffic never moves. If post-switch checks fail, the proxy immediately switches back to the previous image.

Track releases or signed tags rather than deploying a moving branch. This gives every installed version an auditable identity and makes rollback deterministic.

The supervisor must treat both status and request files as untrusted hints: independently resolve the requested version against the configured repository allowlist and verify its signature/digest before taking host-level action.

The update supervisor is intentionally not included yet: its host integration depends on whether production will use plain Docker Compose, Windows services, Docker Swarm, or Kubernetes. The app-facing version endpoint and container boundary are ready for it.

## Offline operation

Normal application and database operation require no internet connection. For a permanently isolated site:

1. Build and test the images on a connected CI worker.
2. Export both the application and Caddy images to signed archives.
3. Transfer and import the archives through the site's approved media process.
4. Give the supervisor a local release manifest directory instead of a GitHub endpoint.

The UI should say **Update status unavailable while offline**, while continuing to serve the installed version.

## Before first production start

1. Create `secrets/db_password.txt` and `secrets/app_users.json` as described in `secrets/README.md`.
2. Copy `.env.example` to `.env` and set the database server and names; do not put passwords there. A fixed SQL Server TCP port (`server,port`) is more reliable from Linux containers than named-instance discovery.
3. Generate and trust Caddy's local root certificate on client machines, or replace `tls internal` with an organization-issued certificate.
4. Build while connected: `docker compose build`.
5. Start: `docker compose up -d`.
6. Confirm that HTTP is not exposed, an incorrect login returns 401, and a saved cost contains the logged-in username.
7. Back up the application database and rehearse both image rollback and database restore.

## Remaining production hardening

- Choose the deployment platform so the update supervisor can be implemented correctly.
- Pin Python dependencies with hashes. Frontend dependencies are already pinned by `pnpm-lock.yaml`.
- Add database-aware readiness checks and structured audit logs for login, save, settings, and update events.
- Replace local passwords with the organization's identity provider when group privileges are introduced.
