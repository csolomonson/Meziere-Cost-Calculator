"""Self-service account routes shared by both co-hosted applications."""

from fastapi import APIRouter, HTTPException, Request

from user_management import UserStoreError, change_own_password
from web.schemas import PasswordChangeRequest


router = APIRouter()


@router.post("/api/account/password")
def change_password(payload: PasswordChangeRequest, request: Request):
    try:
        change_own_password(
            request.state.principal.username,
            payload.current_password,
            payload.new_password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="User was not found") from exc
    except UserStoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"changed": True}
