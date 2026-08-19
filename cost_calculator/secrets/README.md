# Runtime secrets

These files are for direct local-development launches only. Do not commit them.
Create:

- `db_password.txt` containing only the SQL login password.
- `app_users.json` containing a username map. Passwords should be PBKDF2 hashes, for example:

```json
{
  "cole": {
    "password_hash": "pbkdf2_sha256$600000$SALT_HEX$HASH_HEX",
    "groups": ["users", "administrators"]
  }
}
```

Generate a hash with `python tools/hash_password.py` from the project environment.

Administrators can manage this directory from the **User management** button on the home screen. New and replacement passwords must be at least eight characters. The last administrator cannot be deleted or removed from the `administrators` group.

Production does not read this source directory. The native VM installer stores the
SQL password under `/var/lib/cost-calculator/secrets` and the writable user
directory under `/var/lib/cost-calculator/users`, with service-specific
permissions. Both persist when an application release is upgraded or rolled back.
Caddy's separate state is owned by its own Unix account.
