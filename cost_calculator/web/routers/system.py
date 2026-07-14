"""Health, session, version, update, conversion, and shell routes."""

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from app_config import setting
from costing.conversion_calculator import calculate_conversion, calculator_config
from update_contract import request_update, update_status
from web.paths import STATIC_DIR
from web.schemas import ConversionCalculationRequest


router = APIRouter()


@router.get("/api/health")
def health():
    return {"ok": True}


@router.get("/api/session")
def session(request: Request):
    principal = request.state.principal
    return {"username": principal.username, "groups": principal.groups}


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

