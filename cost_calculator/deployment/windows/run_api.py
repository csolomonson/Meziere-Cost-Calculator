"""Native Windows entry point for the Product Cost Calculator API.

WinSW launches this module from the application virtual environment.  Settings
are loaded before Uvicorn imports ``api:app`` so database engines and other
module-level configuration see the service environment on their first import.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import re
import sys
from pathlib import Path
from typing import MutableMapping


APP_ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _environment_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (str, int, float)):
        return str(value)
    raise ValueError("setting values must be strings, numbers, or booleans")


def load_environment(
    path: Path, environ: MutableMapping[str, str] | None = None
) -> MutableMapping[str, str]:
    """Load a JSON settings object without overriding explicit environment values."""
    target = os.environ if environ is None else environ
    try:
        # Windows PowerShell 5.1 writes a UTF-8 BOM by default.  ``utf-8-sig``
        # accepts that output while also reading ordinary UTF-8 JSON.
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Native service settings were not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Could not read native service settings: {path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Native service settings must be a JSON object")

    for name, value in payload.items():
        if not isinstance(name, str) or not ENVIRONMENT_NAME.fullmatch(name):
            raise RuntimeError(f"Invalid environment setting name: {name!r}")
        try:
            normalized = _environment_value(value)
        except ValueError as exc:
            raise RuntimeError(f"Invalid value for environment setting {name}") from exc
        target.setdefault(name, normalized)
    return target


def _bounded_integer(name: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = os.environ.get(name, str(default))
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if not minimum <= value <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return value


def server_options() -> dict:
    """Return the deliberately small, localhost-only Uvicorn service surface."""
    return {
        "host": os.environ.get("COST_APP_HOST", "127.0.0.1"),
        "port": _bounded_integer("COST_APP_PORT", 8000, 1, 65535),
        "workers": _bounded_integer("COST_APP_WORKERS", 2, 1, 32),
        "proxy_headers": True,
        "forwarded_allow_ips": os.environ.get(
            "COST_APP_FORWARDED_ALLOW_IPS", "127.0.0.1"
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the native Windows API service")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path(
            os.environ.get(
                "COST_APP_CONFIG_FILE",
                Path(os.environ.get("PROGRAMDATA", APP_ROOT))
                / "CostCalculator"
                / "native-settings.json",
            )
        ),
        help="JSON file containing the service environment",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_environment(args.config.resolve())
    os.chdir(APP_ROOT)
    # Executing this file makes ``deployment/windows`` sys.path[0]. Add the
    # application root explicitly so Uvicorn workers can import ``api:app``.
    sys.path.insert(0, str(APP_ROOT))

    import uvicorn

    uvicorn.run("api:app", **server_options())


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
