# Optional SQL Server certificate authority

The release image contains Ubuntu's public CA bundle. If SQL Server uses a
certificate issued by an internal authority, add the PEM-encoded root and any
intermediate certificates to the persistent application volume:

```bash
sudo docker run --rm -i \
  --mount source=cost-calculator-data,target=/var/lib/cost-calculator \
  ghcr.io/OWNER/REPOSITORY:v1.2.3 install-ca < company-sql-ca.crt
```

The command validates the PEM input and rebuilds the container's combined trust
bundle. Restart the application container afterward. CA certificates are public
trust material, not private keys; never pass a SQL Server private key to this
command.

Local `.crt` files in this directory remain ignored by Git and the Docker build
context so organization-specific trust chains cannot be published accidentally.
