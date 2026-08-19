# Optional SQL Server certificate authority

If SQL Server uses a certificate issued by an internal certificate authority,
place the PEM-encoded root and any intermediate CA certificates in this directory
with a `.crt` extension before running `deployment/ubuntu/start.sh`. Startup
combines them with Ubuntu's trusted CA bundle and mounts the result read-only into
the application container.

CA certificates are public trust material, not private keys. Do not place a SQL
Server private key here. Local `.crt` files are ignored by Git and the Docker build
context so each server can use its organization-specific trust chain without
publishing it in the release image or bundle.
