"""Health, session, version, update, conversion, and shell routes."""

import json
import logging

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import text

from app_config import setting
from costing.conversion_calculator import calculate_conversion, calculator_config
from update_contract import request_update, update_status
from utils.erp_cursor import app_cnxn, erp_cnxn
from web.paths import STATIC_DIR
from web.schemas import ConversionCalculationRequest


router = APIRouter()
logger = logging.getLogger(__name__)


SIGNED_OUT_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Signed out</title>
  <style>
    body { background: #f4f7fb; color: #172033; display: grid; font-family: system-ui, sans-serif; margin: 0; min-height: 100vh; place-items: center; }
    main { background: #fff; border: 1px solid #d7dee8; border-radius: 12px; box-shadow: 0 12px 32px #1b2b4b1a; max-width: 420px; padding: 32px; text-align: center; }
    h1 { margin: 0 0 10px; }
    p { color: #5f6b7a; margin: 0 0 22px; }
    a { background: #245bc7; border-radius: 7px; color: #fff; display: inline-block; font-weight: 800; padding: 10px 16px; text-decoration: none; }
  </style>
</head>
<body><main><h1>Signed out</h1><p>Your Meziere application credentials have been cleared from this browser.</p><a href="/">Sign in again</a></main></body>
</html>"""


@router.get("/api/health")
def health():
    return {"ok": True}


@router.get("/api/ready")
def readiness():
    """Confirm that both required SQL Server databases are reachable."""
    unavailable = []
    for name, engine in (("erp", erp_cnxn), ("costing", app_cnxn)):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            logger.exception("%s database readiness check failed", name)
            unavailable.append(name)
    if unavailable:
        raise HTTPException(status_code=503, detail="Required database connectivity is unavailable.")
    return {"ok": True, "databases": ["erp", "costing"]}


@router.get("/api/session")
def session(request: Request):
    principal = request.state.principal
    return {"username": principal.username, "groups": principal.groups}


@router.get("/logout", response_class=HTMLResponse)
def logout():
    return HTMLResponse(
        SIGNED_OUT_HTML,
        headers={
            "Clear-Site-Data": '"cache", "cookies", "storage"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/api/version")
def version():
    return {
        "version": setting("APP_VERSION", "development"),
        "repository": setting("APP_REPOSITORY", ""),
    }


@router.get("/api/update")
def get_update(request: Request):
    status = update_status()
    status["can_install"] = "administrators" in request.state.principal.groups
    return status


@router.post("/api/update/install")
def install_update(request: Request):
    principal = request.state.principal
    if "administrators" not in principal.groups:
        raise HTTPException(status_code=403, detail="Administrator access is required")
    try:
        requested = request_update(principal.username)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"accepted": True, **requested}


@router.get("/api/conversion-calculator")
def conversion_calculator_settings():
    return calculator_config()


@router.post("/api/conversion-calculator/calculate")
def conversion_calculator_calculate(request: ConversionCalculationRequest):
    try:
        return calculate_conversion(request.mode, request.values, request.multiplier)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/")
def index(request: Request):
    principal = request.state.principal
    session_json = json.dumps(
        {"username": principal.username, "groups": principal.groups}
    ).replace("<", "\\u003c")
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8").replace(
        "__SESSION_JSON__", session_json
    )
    return HTMLResponse(html)
