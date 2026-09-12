from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
from uuid import uuid4

from .session import UserSession


class MasterClientError(RuntimeError):
    """The CLI could not complete a Master API request."""


@dataclass(frozen=True)
class MasterApiError(MasterClientError):
    status_code: int
    code: str
    message: str
    request_id: str

    def __str__(self) -> str:
        return f"Master API error {self.status_code} {self.code}: {self.message}"


class MasterClient:
    """Authenticated HTTP boundary for CLI business-resource operations."""

    def __init__(
        self,
        session: UserSession,
        base_url: str = "http://localhost:8000",
        opener: Callable[..., Any] | None = None,
    ):
        self.session = session
        self.base_url = base_url.rstrip("/")
        self.opener = opener or build_opener().open

    def get(self, path: str, request_id: str | None = None) -> dict[str, Any]:
        return self._request("GET", path, request_id=request_id)

    def create(
        self,
        path: str,
        payload: dict[str, Any],
        request_id: str | None = None,
    ) -> dict[str, Any]:
        return self._request("POST", path, payload, request_id)

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        request_id = request_id or str(uuid4())
        url = f"{self.base_url}/{path.lstrip('/')}"
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": self.session.authorization,
            "X-Request-ID": request_id,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with self.opener(request, timeout=5) as response:
                return self._decode(response.getcode(), response.read(), request_id)
        except HTTPError as exc:
            return self._decode_error(exc.code, exc.read(), request_id)
        except (URLError, OSError) as exc:
            raise MasterClientError("Master service is unavailable") from exc

    def _decode(self, status_code: int, raw_body: bytes, request_id: str) -> dict[str, Any]:
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise MasterClientError("Master returned an invalid JSON response") from exc
        if not isinstance(body, dict):
            raise MasterClientError("Master returned an invalid response")
        if status_code >= 400:
            return self._raise_api_error(status_code, body, request_id)
        return body

    def _decode_error(self, status_code: int, raw_body: bytes, request_id: str) -> dict[str, Any]:
        try:
            body = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            body = {}
        if not isinstance(body, dict):
            body = {}
        return self._raise_api_error(status_code, body, request_id)

    @staticmethod
    def _raise_api_error(status_code: int, body: dict[str, Any], request_id: str) -> dict[str, Any]:
        code = body.get("code")
        message = body.get("message")
        response_request_id = body.get("request_id")
        if not all(isinstance(value, str) and value for value in (code, message, response_request_id)):
            raise MasterClientError("Master returned an invalid API error")
        raise MasterApiError(status_code, code, message, response_request_id or request_id)
