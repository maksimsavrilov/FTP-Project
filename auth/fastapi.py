from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .service import AuthenticationBackendUnavailable, authorize, create_client


def create_app(client=None) -> FastAPI:
    app = FastAPI()
    backend = client or create_client()

    @app.post("/v1/authorize")
    async def authorization(request: Request) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        authorization_header = request.headers.get("Authorization", "")
        scheme, _, credential = authorization_header.partition(" ")
        if scheme.lower() != "bearer" or not credential:
            status, body = authorize(backend, None, None, None, None, request_id)
            return JSONResponse(content=body, status_code=status, headers={"X-Request-ID": request_id})
        try:
            body = await request.json()
        except ValueError:
            return JSONResponse(
                content={"code": "INVALID_REQUEST", "message": "request body must be valid JSON", "request_id": request_id},
                status_code=400,
                headers={"X-Request-ID": request_id},
            )
        if not isinstance(body, dict):
            return JSONResponse(
                content={"code": "INVALID_REQUEST", "message": "request body must be an object", "request_id": request_id},
                status_code=400,
                headers={"X-Request-ID": request_id},
            )
        try:
            status, response_body = authorize(
                backend,
                credential,
                body.get("resource"),
                body.get("action"),
                body.get("context"),
                request_id,
            )
        except AuthenticationBackendUnavailable:
            status, response_body = 503, {
                "code": "AUTH_SERVICE_UNAVAILABLE",
                "message": "authentication backend is unavailable",
                "request_id": request_id,
            }
        return JSONResponse(content=response_body, status_code=status, headers={"X-Request-ID": request_id})

    return app
