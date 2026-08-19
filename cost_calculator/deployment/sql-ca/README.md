# Optional SQL Server certificate authority

The VM uses Ubuntu's system CA bundle. If SQL Server uses a certificate issued by
an internal authority, install the PEM-encoded public root and intermediate
certificates:

```bash
sudo bash deployment/ubuntu/install-sql-ca.sh company-root.crt company-intermediate.crt
```

The command validates the PEM input, updates the host trust bundle, and restarts
the application service. CA certificates are public trust material, not private
keys; never pass a SQL Server private key to this command.

Local `.crt` files in this directory remain ignored by Git so
organization-specific trust chains cannot be published accidentally.
