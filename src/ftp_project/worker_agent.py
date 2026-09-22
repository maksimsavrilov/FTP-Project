from __future__ import annotations

from typing import Any, Callable

from .master import MasterClient
from .session import UserSession


class WorkerAgentMasterClient(MasterClient):
    """Authenticated Worker Agent boundary for reports sent to Master."""

    def __init__(
        self,
        access_token: str,
        token_type: str = "Bearer",
        base_url: str = "http://localhost:8000",
        opener: Callable[..., Any] | None = None,
    ):
        super().__init__(UserSession(access_token, token_type), base_url, opener)

    def report_web_service_actual_state(
        self,
        service_id: str,
        assignment_id: str,
        version: int,
        status: str,
        configuration: dict[str, Any],
        health: dict[str, Any],
        observed_at: str,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self.create(
            f"/v1/services/{service_id}/actual-state",
            {
                "assignment_id": assignment_id,
                "version": version,
                "status": status,
                "configuration": configuration,
                "health": health,
                "observed_at": observed_at,
            },
            request_id=request_id,
        )
