"""Runtime settings with environment and secret-file support."""

import os
from pathlib import Path


LOCAL_SECRETS_DIR = Path(__file__).resolve().parent / "secrets"


def setting(name: str, default: str | None = None, *, required: bool = False) -> str | None:
    file_name = os.getenv(f"{name}_FILE")
    if file_name:
        try:
            value = Path(file_name).read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Could not read secret file configured by {name}_FILE") from exc
    else:
        value = os.getenv(name, default)
    if required and not value:
        raise RuntimeError(f"{name} or {name}_FILE must be configured")
    return value


def boolean_setting(name: str, default: bool) -> bool:
    value = setting(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def secret_setting(name: str, local_filename: str, default: str | None = None) -> str | None:
    """Read configured secret first, then the ignored local secrets directory.

    The local fallback keeps direct development launches convenient.
    Production should continue to provide ``NAME_FILE`` explicitly.
    """
    value = setting(name)
    if value is not None:
        return value
    local_path = LOCAL_SECRETS_DIR / local_filename
    if local_path.is_file():
        try:
            return local_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise RuntimeError(f"Could not read local secret {local_filename}") from exc
    return default


def secret_file_path(name: str, local_filename: str) -> Path | None:
    """Return the writable backing file for a file-managed secret, if any."""
    configured_path = os.getenv(f"{name}_FILE")
    if configured_path:
        return Path(configured_path)
    if os.getenv(name) is not None:
        return None
    local_path = LOCAL_SECRETS_DIR / local_filename
    return local_path if local_path.is_file() else None
