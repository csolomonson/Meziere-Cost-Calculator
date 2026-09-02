"""Atomic administration of the file-backed application user directory."""

import json
import os
import re
import time
from contextlib import contextmanager
from pathlib import Path
from threading import Lock

from app_config import secret_file_path
from authentication import password_hash, password_matches_record


ADMIN_GROUP = "administrators"
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.@-]{1,100}$")
GROUP_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
_PROCESS_LOCK = Lock()


class UserStoreError(RuntimeError):
    pass


class UserConflictError(UserStoreError):
    pass


def _users_path() -> Path:
    path = secret_file_path("COST_APP_USERS_JSON", "app_users.json")
    if path is None:
        raise UserStoreError(
            "User management requires COST_APP_USERS_JSON_FILE or a local secrets/app_users.json file"
        )
    return path


@contextmanager
def _file_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + 5
    descriptor = None
    while descriptor is None:
        try:
            descriptor = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > 30:
                    lock_path.unlink()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() >= deadline:
                raise UserStoreError("The user directory is busy; try again")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(descriptor)
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _normalize_users(raw_users: dict) -> dict[str, dict]:
    return {
        username: ({"password_hash": value, "groups": []} if isinstance(value, str) else dict(value))
        for username, value in raw_users.items()
    }


def _read(path: Path) -> dict[str, dict]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UserStoreError("Could not read the application user directory") from exc
    if not isinstance(payload, dict):
        raise UserStoreError("The application user directory must be a JSON object")
    return _normalize_users(payload)


def _write(path: Path, users: dict[str, dict]) -> None:
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(users, indent=2) + "\n", encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, path)
    except OSError as exc:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise UserStoreError("The application user directory is not writable") from exc


def _groups(groups) -> list[str]:
    clean = []
    for group in groups or []:
        group = str(group).strip()
        if not GROUP_PATTERN.fullmatch(group):
            raise ValueError(f"Invalid group name: {group or '(blank)'}")
        if group not in clean:
            clean.append(group)
    return clean


def _validate_username(username: str) -> str:
    username = username.strip()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username may contain letters, numbers, dot, dash, underscore, and @")
    return username


def _public_users(users: dict[str, dict]) -> list[dict]:
    return [
        {"username": username, "groups": list(record.get("groups", []))}
        for username, record in sorted(users.items(), key=lambda item: item[0].lower())
    ]


def list_users() -> list[dict]:
    with _PROCESS_LOCK:
        return _public_users(_read(_users_path()))


def add_user(username: str, password: str, groups) -> list[dict]:
    username = _validate_username(username)
    clean_groups = _groups(groups)
    with _PROCESS_LOCK:
        path = _users_path()
        with _file_lock(path):
            users = _read(path)
            if username in users:
                raise UserConflictError(f"User {username} already exists")
            users[username] = {"password_hash": password_hash(password), "groups": clean_groups}
            _write(path, users)
            return _public_users(users)


def update_user(username: str, password: str | None, groups: list[str] | None) -> list[dict]:
    username = _validate_username(username)
    with _PROCESS_LOCK:
        path = _users_path()
        with _file_lock(path):
            users = _read(path)
            if username not in users:
                raise KeyError(username)
            record = users[username]
            if groups is not None:
                clean_groups = _groups(groups)
                other_admins = sum(
                    ADMIN_GROUP in item.get("groups", []) for name, item in users.items() if name != username
                )
                if ADMIN_GROUP in record.get("groups", []) and ADMIN_GROUP not in clean_groups and not other_admins:
                    raise UserConflictError("The last administrator cannot lose administrator access")
                record["groups"] = clean_groups
            if password is not None:
                record.pop("password", None)
                record["password_hash"] = password_hash(password)
            _write(path, users)
            return _public_users(users)


def change_own_password(username: str, current_password: str, new_password: str) -> None:
    if len(new_password) < 8:
        raise ValueError("New password must be at least 8 characters")
    with _PROCESS_LOCK:
        path = _users_path()
        with _file_lock(path):
            users = _read(path)
            if username not in users:
                raise KeyError(username)
            record = users[username]
            if not password_matches_record(current_password, record):
                raise ValueError("Current password is incorrect")
            record.pop("password", None)
            record["password_hash"] = password_hash(new_password)
            _write(path, users)


def delete_user(username: str) -> list[dict]:
    username = _validate_username(username)
    with _PROCESS_LOCK:
        path = _users_path()
        with _file_lock(path):
            users = _read(path)
            if username not in users:
                raise KeyError(username)
            if ADMIN_GROUP in users[username].get("groups", []):
                other_admins = sum(
                    ADMIN_GROUP in item.get("groups", []) for name, item in users.items() if name != username
                )
                if not other_admins:
                    raise UserConflictError("The last administrator cannot be deleted")
            del users[username]
            _write(path, users)
            return _public_users(users)
