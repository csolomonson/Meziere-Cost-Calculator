"""Authorization and API error translation helpers."""

from fastapi import HTTPException, Request

from user_management import UserConflictError


def require_administrator(request: Request):
    if "administrators" not in request.state.principal.groups:
        raise HTTPException(status_code=403, detail="Administrator access is required")


def user_management_error(exc: Exception):
    if isinstance(exc, KeyError):
        raise HTTPException(status_code=404, detail="User was not found") from exc
    if isinstance(exc, (UserConflictError, ValueError)):
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    raise HTTPException(status_code=503, detail=str(exc)) from exc

