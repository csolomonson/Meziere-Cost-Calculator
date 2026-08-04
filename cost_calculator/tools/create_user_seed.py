"""Interactively create the initial administrator JSON without echoing a password."""

from __future__ import annotations

import getpass
import json
import re
import sys

from authentication import password_hash


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,100}$")


def main() -> None:
    if len(sys.argv) != 2 or not USERNAME_PATTERN.fullmatch(sys.argv[1]):
        raise SystemExit("Provide one valid administrator username")
    password = getpass.getpass("Application password (12+ characters): ")
    confirmation = getpass.getpass("Confirm application password: ")
    if password != confirmation:
        raise SystemExit("Passwords did not match")
    if len(password) < 12:
        raise SystemExit("The initial administrator password must be at least 12 characters")
    payload = {
        sys.argv[1]: {
            "password_hash": password_hash(password),
            "groups": ["users", "administrators"],
        }
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
