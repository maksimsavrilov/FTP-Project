from __future__ import annotations

import json
from collections.abc import Callable
from time import sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4


class WebAgentClientError(RuntimeError):
    """The Web Agent returned an invalid or rejected response."""


class WebAgentUnavailable(WebAgentClientError):
    """The Web Agent could not handle the desired-state request."""


class WebAgentClient:
    """HTTP boundary for Master requests sent to a selected Web Agent."""

    def __init__(
        self,
        base_url: str,
        credential: str,
        timeout: float = 5.0,
        max_retries: int = 2,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = sleep,
    ):
        if not base_url:
            raise ValueError("base_url is required")
        if not credential:
            raise ValueError("credential is required")
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.base_url = base_url.rstrip("/")
        self.credential = credential
        self.timeout = timeout
        self.max_retries = max_retries
        self.opener = opener
        self.sleeper = sleeper

    def send_desired_state(
        self,
        service_id: str,
        assignment_id: str,
        version: int,
        lifecycle_state: str,
        configuration: dict[str, Any],
        request_id: str | None = None,
        *,
        agent_url: str | None = None,
    ) -> dict[str, Any]:
        if not service_id:
            raise ValueError("service_id is required")
        if not assignment_id:
            raise ValueError("assignment_id is required")
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise ValueError("version must be positive")
        if not lifecycle_state:
            raise ValueError("lifecycle_state is required")
        if not isinstance(configuration, dict):
            raise TypeError("configuration must be an object")

        request_id = request_id or str(uuid4())
        payload = json.dumps(
            {
                "service_type": "WEB",
                "assignment_id": assignment_id,
                "version": version,
                "lifecycle_state": lifecycle_state,
                "configuration": configuration,
            }
        ).encode("utf-8")
        target_url = (agent_url or self.base_url).rstrip("/")
        request = Request(
            f"{target_url}/v1/services/{quote(service_id, safe='')}/desired-state",
            data=payload,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.credential}",
                "Content-Type": "application/json",
                "X-Request-ID": request_id,
            },
            method="POST",
        )

        for attempt in range(self.max_retries + 1):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    status = response.getcode()
                    body = self._read_json(response)
            except HTTPError as exc:
                status = exc.code
                body = self._read_json(exc, allow_empty=True)
            except (URLError, TimeoutError, OSError) as exc:
                if attempt < self.max_retries:
                    self.sleeper(0.1 * (2**attempt))
                    continue
                raise WebAgentUnavailable("Web Agent is unavailable") from exc

            if status in {500, 502, 503, 504}:
                if attempt < self.max_retries:
                    self.sleeper(0.1 * (2**attempt))
                    continue
                raise WebAgentUnavailable("Web Agent is unavailable")
            if status >= 400:
                message = body.get("message")
                raise WebAgentClientError(
                    message
                    if isinstance(message, str)
                    else "Web Agent rejected desired state"
                )
            self._validate_acknowledgement(body, service_id, version)
            return body

        raise WebAgentUnavailable("Web Agent is unavailable")

    @staticmethod
    def _read_json(response: Any, allow_empty: bool = False) -> dict[str, Any]:
        try:
            body = json.loads(response.read().decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            if allow_empty:
                return {}
            raise WebAgentClientError("Web Agent returned invalid JSON") from exc
        if not isinstance(body, dict):
            raise WebAgentClientError("Web Agent response must be an object")
        return body

    @staticmethod
    def _validate_acknowledgement(
        body: dict[str, Any], service_id: str, version: int
    ) -> None:
        if (
            body.get("accepted") is not True
            or body.get("service_id") != service_id
            or body.get("version") != version
        ):
            raise WebAgentClientError("Web Agent returned an invalid acknowledgement")
