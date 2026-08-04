"""Invoke the isolated .NET Framework Crystal Reports renderer."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from app_config import secret_setting, setting


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RENDERER = (
    BASE_DIR
    / "reporting"
    / "CrystalReportRenderer"
    / "bin"
    / "Release"
    / "CrystalReportRenderer.exe"
)
DEFAULT_REPORT = BASE_DIR / "reports" / "PartCost.rpt"


class ReportConfigurationError(RuntimeError):
    """The renderer executable, report, or required setting is unavailable."""


class ReportRenderError(RuntimeError):
    """Crystal Reports could not produce a valid PDF."""


class ReportRenderTimeout(ReportRenderError):
    """Crystal Reports exceeded its configured render deadline."""


def _configured_path(name: str, default: Path) -> Path:
    value = setting(name)
    path = Path(value) if value else default
    if not path.is_absolute():
        path = BASE_DIR / path
    return path.resolve()


def _timeout_seconds() -> int:
    raw_value = setting("CRYSTAL_RENDER_TIMEOUT_SECONDS", "60") or "60"
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ReportConfigurationError(
            "CRYSTAL_RENDER_TIMEOUT_SECONDS must be an integer"
        ) from exc
    if not 5 <= value <= 300:
        raise ReportConfigurationError(
            "CRYSTAL_RENDER_TIMEOUT_SECONDS must be between 5 and 300"
        )
    return value


def _render_payload(part_cost_id: int, report_path: Path) -> dict:
    password = secret_setting("COST_DB_PASSWORD", "db_password.txt", "") or ""
    username = setting("COST_DB_USERNAME", "cost_app_access") or ""
    if not username or not password:
        raise ReportConfigurationError(
            "Database credentials are required for Crystal Reports"
        )
    return {
        "reportPath": str(report_path),
        "parameterName": setting(
            "CRYSTAL_PART_COST_PARAMETER", "PartCostID"
        )
        or "PartCostID",
        "partCostId": int(part_cost_id),
        "server": setting("COST_DB_SERVER", "localhost\\MEZIEREDB22") or "",
        "database": setting("COST_APP_DATABASE", "M2_ME") or "",
        "username": username,
        "password": password,
    }


def render_part_cost_pdf(part_cost_id: int) -> bytes:
    """Render one saved cost while keeping its SQL password off the command line."""
    renderer_path = _configured_path("CRYSTAL_RENDERER_PATH", DEFAULT_RENDERER)
    report_path = _configured_path("CRYSTAL_PART_COST_REPORT", DEFAULT_REPORT)
    if not renderer_path.is_file():
        raise ReportConfigurationError("The Crystal renderer executable is missing")
    if not report_path.is_file():
        raise ReportConfigurationError("The Part Cost Crystal report is missing")

    request = _render_payload(part_cost_id, report_path)
    payload = json.dumps(request, separators=(",", ":")).encode("utf-8")
    creation_flags = (
        getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    )
    try:
        completed = subprocess.run(
            [str(renderer_path)],
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=_timeout_seconds(),
            check=False,
            creationflags=creation_flags,
        )
    except subprocess.TimeoutExpired as exc:
        raise ReportRenderTimeout("Crystal Reports timed out") from exc
    except OSError as exc:
        raise ReportRenderError("The Crystal renderer could not be started") from exc

    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        detail = detail.replace(request["password"], "[redacted]")
        if len(detail) > 2000:
            detail = detail[-2000:]
        raise ReportRenderError(detail or "Crystal Reports returned an error")
    if not completed.stdout.startswith(b"%PDF-"):
        raise ReportRenderError("Crystal Reports returned an invalid PDF")
    return completed.stdout
