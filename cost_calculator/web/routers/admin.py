"""File-backed user administration routes."""

from fastapi import APIRouter, Request

from user_management import (
    UserStoreError,
    add_user,
    delete_user,
    list_users,
    update_user,
)
from web.dependencies import require_administrator, user_management_error
from web.schemas import UserCreateRequest, UserUpdateRequest


router = APIRouter()


@router.get("/api/admin/users")
def get_users(request: Request):
    require_administrator(request)
    try:
        return {"users": list_users()}
    except UserStoreError as exc:
        user_management_error(exc)


@router.post("/api/admin/users")
def create_user(payload: UserCreateRequest, request: Request):
    require_administrator(request)
    try:
        return {"users": add_user(payload.username, payload.password, payload.groups)}
    except (UserStoreError, ValueError) as exc:
        user_management_error(exc)


@router.put("/api/admin/users/{username}")
def change_user(username: str, payload: UserUpdateRequest, request: Request):
    require_administrator(request)
    try:
        return {"users": update_user(username, payload.password, payload.groups)}
    except (UserStoreError, ValueError, KeyError) as exc:
        user_management_error(exc)


@router.delete("/api/admin/users/{username}")
def remove_user(username: str, request: Request):
    require_administrator(request)
    try:
        return {"users": delete_user(username)}
    except (UserStoreError, ValueError, KeyError) as exc:
        user_management_error(exc)

