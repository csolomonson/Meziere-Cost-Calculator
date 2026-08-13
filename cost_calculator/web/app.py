"""FastAPI application composition."""

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles

from authentication import AuthenticationError, authenticate_request
from web.paths import STATIC_DIR
from web.routers import admin, catalog, costs, reports, settings, system


app = FastAPI(title="Product Cost Calculator", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.middleware("http")
async def require_authentication(request: Request, call_next):
    if request.url.path in {"/api/health", "/api/ready"}:
        return await call_next(request)
    try:
        request.state.principal = authenticate_request(request)
    except AuthenticationError:
        return JSONResponse(
            {"detail": "Authentication required"},
            status_code=401,
            headers={
                "WWW-Authenticate": (
                    'Basic realm="Product Cost Calculator", charset="UTF-8"'
                )
            },
        )
    except RuntimeError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=503)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


def _register_routes(router: APIRouter) -> None:
    """Flatten a feature router into ``app.routes``.

    FastAPI's current lazy ``include_router`` implementation exposes internal
    wrapper objects in ``app.routes``.  The original application exposed
    concrete ``APIRoute`` instances, so clone each route through the app's
    router to preserve that public inspection contract and dependency override
    behavior.
    """

    for route in router.routes:
        if not isinstance(route, APIRoute):
            raise TypeError(f"Unsupported route type: {type(route).__name__}")
        app.router.add_api_route(
            route.path,
            route.endpoint,
            response_model=route.response_model,
            status_code=route.status_code,
            tags=route.tags,
            dependencies=route.dependencies,
            summary=route.summary,
            description=route.description,
            response_description=route.response_description,
            responses=route.responses,
            deprecated=route.deprecated,
            methods=route.methods,
            operation_id=route.operation_id,
            response_model_include=route.response_model_include,
            response_model_exclude=route.response_model_exclude,
            response_model_by_alias=route.response_model_by_alias,
            response_model_exclude_unset=route.response_model_exclude_unset,
            response_model_exclude_defaults=route.response_model_exclude_defaults,
            response_model_exclude_none=route.response_model_exclude_none,
            include_in_schema=route.include_in_schema,
            response_class=route.response_class,
            name=route.name,
            callbacks=route.callbacks,
            openapi_extra=route.openapi_extra,
            generate_unique_id_function=route.generate_unique_id_function,
            strict_content_type=route.strict_content_type,
        )


for feature_router in (
    system.router,
    admin.router,
    catalog.router,
    settings.router,
    costs.router,
    reports.router,
):
    _register_routes(feature_router)
