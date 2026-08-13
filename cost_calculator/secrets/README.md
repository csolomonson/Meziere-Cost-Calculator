# Runtime secrets

Do not commit files in this directory. Create:

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
