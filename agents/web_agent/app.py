from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, ValidationError


class DesiredWebServiceState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service_type: str
    assignment_id: str
    version: int
    lifecycle_state: str
    configuration: dict[str, Any]


class WebAgentDesiredStateStore:
    """Small process-local store for the accepted desired version per service."""

    def __init__(self) -> None:
        self._states: dict[str, DesiredWebServiceState] = {}

    def get(self, service_id: str) -> DesiredWebServiceState | None:
        return self._states.get(service_id)

    def accept(self, service_id: str, state: DesiredWebServiceState) -> tuple[bool, str | None]:
        current = self._states.get(service_id)
        if current is not None and state.version < current.version:
            return False, "stale desired-state version"
        if current is None or state.version > current.version:
            self._states[service_id] = state
        return True, None

    def report_actual_state(
        self,
        service_id: str,
        client: Any,
        *,
        status: str,
        health: dict[str, Any],
        observed_at: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        state = self._states.get(service_id)
        if state is None:
            raise LookupError(f"{service_id} has no accepted desired state")

        return client.report_web_service_actual_state(
            service_id,
            state.assignment_id,
            state.version,
            status,
            state.configuration,
            health,
            observed_at,
            request_id=request_id,
        )


def create_app(
    master_token: str | None = None,
    store: WebAgentDesiredStateStore | None = None,
) -> FastAPI:
    """Build the authenticated Web Agent desired-state HTTP boundary."""

    app = FastAPI(title="Web Agent", version="1.0.0")
    expected_token = master_token if master_token is not None else os.environ.get("MASTER_AGENT_TOKEN", "")
    desired_states = store or WebAgentDesiredStateStore()

    def request_id(request: Request) -> str:
        return request.headers.get("X-Request-ID", "")

    def error(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
        request_id_value = request_id(request)
        return JSONResponse(
            status_code=status_code,
            content={"code": code, "message": message, "request_id": request_id_value},
            headers={"X-Request-ID": request_id_value},
        )

    def authenticated(request: Request) -> bool:
        scheme, _, credential = request.headers.get("Authorization", "").partition(" ")
        return (
            bool(expected_token)
            and scheme.lower() == "bearer"
            and bool(credential)
            and hmac.compare_digest(credential, expected_token)
        )

    @app.post("/v1/services/{service_id}/desired-state")
    async def receive_desired_state(service_id: str, request: Request) -> JSONResponse:
        if not authenticated(request):
            return error(request, 401, "AUTHENTICATION_FAILED", "authentication required")
        try:
            payload = await request.json()
            state = DesiredWebServiceState.model_validate(payload)
        except (ValueError, ValidationError):
            return error(request, 400, "INVALID_REQUEST", "desired state is invalid")
        if not service_id:
            return error(request, 400, "INVALID_REQUEST", "service_id is required")
        if state.service_type != "WEB":
            return error(request, 400, "UNSUPPORTED_SERVICE_TYPE", "Web Agent accepts WEB services only")
        if state.version < 1:
            return error(request, 400, "INVALID_REQUEST", "version must be positive")

        accepted, rejection = desired_states.accept(service_id, state)
        if not accepted:
            return error(request, 409, "STALE_DESIRED_STATE", rejection or "desired state was rejected")
        return JSONResponse(
            status_code=202,
            content={"accepted": True, "service_id": service_id, "version": state.version},
            headers={"X-Request-ID": request_id(request)},
        )

    @app.get("/v1/services/{service_id}/reconciliation")
    async def get_reconciliation(service_id: str, request: Request) -> JSONResponse:
        if not authenticated(request):
            return error(request, 401, "AUTHENTICATION_FAILED", "authentication required")
        if not service_id:
            return error(request, 400, "INVALID_REQUEST", "service_id is required")

        state = desired_states.get(service_id)
        if state is None:
            return error(request, 404, "NOT_FOUND", "desired state was not accepted")

        return JSONResponse(
            status_code=200,
            content={
                "service_id": service_id,
                "service_type": state.service_type,
                "assignment_id": state.assignment_id,
                "version": state.version,
                "lifecycle_state": state.lifecycle_state,
                "configuration": state.configuration,
                "status": "ACCEPTED",
            },
            headers={"X-Request-ID": request_id(request)},
        )

    return app
