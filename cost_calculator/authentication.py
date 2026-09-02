"""Authentication boundary designed to grow into group authorization later."""

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import threading
import time
from dataclasses import dataclass

from fastapi import Request

from app_config import boolean_setting, secret_setting, setting


@dataclass(frozen=True)
class Principal:
    username: str
    groups: tuple[str, ...] = ()


class AuthenticationError(Exception):
    pass


class AuthorizationError(Exception):
    pass


def authorize_costing(principal: Principal) -> None:
    if not {"users", "administrators"}.intersection(principal.groups):
        raise AuthorizationError("Membership in users is required")


_AUTH_CACHE_KEY = secrets.token_bytes(32)
_AUTH_CACHE: dict[bytes, float] = {}
_AUTH_CACHE_LOCK = threading.Lock()


def _cache_lifetime() -> float:
    try:
        return max(0.0, min(3600.0, float(setting("COST_APP_AUTH_CACHE_SECONDS", "300") or 0)))
    except ValueError:
        return 300.0


def _credential_cache_key(username: str, password: str, user: dict) -> bytes:
    configured_credential = user.get("password_hash") or user.get("password") or ""
    payload = f"{username}\0{password}\0{configured_credential}".encode()
    return hmac.digest(_AUTH_CACHE_KEY, payload, "sha256")


def _is_cached(cache_key: bytes) -> bool:
    now = time.monotonic()
    with _AUTH_CACHE_LOCK:
        expires_at = _AUTH_CACHE.get(cache_key, 0)
        if expires_at > now:
            return True
        _AUTH_CACHE.pop(cache_key, None)
    return False


def _cache_success(cache_key: bytes) -> None:
    lifetime = _cache_lifetime()
    if not lifetime:
        return
    now = time.monotonic()
    with _AUTH_CACHE_LOCK:
        if len(_AUTH_CACHE) >= 2048:
            _AUTH_CACHE.clear()
        _AUTH_CACHE[cache_key] = now + lifetime


def _verify_pbkdf2(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt, expected = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt), int(iterations)
        ).hex()
    except (TypeError, ValueError):
        return False
    return secrets.compare_digest(actual, expected)


def password_hash(password: str, iterations: int = 600_000) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest}"


def configured_users() -> dict[str, dict]:
    users_json = secret_setting("COST_APP_USERS_JSON", "app_users.json")
    if users_json:
        try:
            raw_users = json.loads(users_json)
        except json.JSONDecodeError as exc:
            raise RuntimeError("COST_APP_USERS_JSON must contain valid JSON") from exc
        return {
            username: ({"password_hash": value, "groups": []} if isinstance(value, str) else value)
            for username, value in raw_users.items()
        }

    username = setting("COST_APP_USERNAME")
    password = setting("COST_APP_PASSWORD")
    password_digest = setting("COST_APP_PASSWORD_HASH")
    if username and (password or password_digest):
        return {username: {"password": password, "password_hash": password_digest, "groups": ["users"]}}
    return {}


def authenticate_request(request: Request) -> Principal:
    if not boolean_setting("COST_APP_AUTH_REQUIRED", True):
        return Principal(
            setting("COST_APP_DEV_USERNAME", "developer") or "developer",
            ("users",),
        )
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        raise AuthenticationError
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode()
        username, password = decoded.split(":", 1)
    except (binascii.Error, ValueError, UnicodeDecodeError):
        raise AuthenticationError from None

    user = configured_users().get(username)
    if not user:
        _verify_pbkdf2(password, "pbkdf2_sha256$1$00$00")
        raise AuthenticationError
    cache_key = _credential_cache_key(username, password, user)
    if _is_cached(cache_key):
        return Principal(username, tuple(user.get("groups", ())))
    if user.get("password_hash"):
        valid = _verify_pbkdf2(password, user["password_hash"])
    else:
        valid = user.get("password") is not None and secrets.compare_digest(password, str(user["password"]))
    if not valid:
        raise AuthenticationError
    _cache_success(cache_key)
    return Principal(username, tuple(user.get("groups", ())))


def authenticate_costing_request(request: Request) -> Principal:
    """Authenticate a request and enforce access to the costing application."""
    principal = authenticate_request(request)
    authorize_costing(principal)
    return principal
