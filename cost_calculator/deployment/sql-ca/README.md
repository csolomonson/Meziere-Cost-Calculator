# Optional SQL Server certificate authority

If SQL Server uses a certificate issued by an internal certificate authority,
place the PEM-encoded root and any intermediate CA certificates in this directory
with a `.crt` extension before building the production image. The Docker build
adds them to the container trust store.

CA certificates are public trust material, not private keys. Do not place a SQL
Server private key here. Local `.crt` files are ignored by Git so each deployment
can use its organization-specific trust chain.
