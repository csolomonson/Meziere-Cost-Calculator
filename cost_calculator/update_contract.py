"""File-based, privilege-separated contract with a host update supervisor."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app_config import setting


def update_status() -> dict:
    current = setting("APP_VERSION", "development")
    status_path = setting("UPDATE_STATUS_FILE")
    default = {
        "status": "unconfigured" if not status_path else "offline",
        "current_version": current,
        "update_available": False,
    }
    if not status_path:
        return default
    try:
        payload = json.loads(Path(status_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return {
        **default,
        "status": str(payload.get("status", "offline")),
        "current_version": current,
        "available_version": payload.get("available_version"),
        "release_url": payload.get("release_url"),
        "update_available": bool(payload.get("update_available")),
    }


def request_update(username: str) -> dict:
    status = update_status()
    if not status["update_available"] or not status.get("available_version"):
        raise ValueError("No update is currently available")
    request_path = setting("UPDATE_REQUEST_FILE", required=True)
    destination = Path(request_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "request_id": str(uuid4()),
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": username,
        "requested_version": status["available_version"],
    }
    temporary = destination.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(temporary, destination)
    return payload
