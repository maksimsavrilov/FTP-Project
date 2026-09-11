from __future__ import annotations

import json
from dataclasses import dataclass
from time import sleep
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class AuthenticationClientError(RuntimeError):
    """The Authentication Service returned an invalid or unusable response."""


class AuthenticationServiceUnavailable(AuthenticationClientError):
    """The Authentication Service could not handle the authorization request."""


@dataclass(frozen=True)
class Principal:
    subject_id: str
    subject_type: str
    scopes: list[str]
    expires_at: str | None = None


@dataclass(frozen=True)
class AuthorizationDecision:
    allowed: bool
    principal: Principal | None
    request_id: str


class AuthenticationClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        max_retries: int = 2,
        opener: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = sleep,
    ):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.opener = opener
        self.sleeper = sleeper

    def authorize(
        self,
        credential: str,
        resource: str,
        action: str,
        context: object | None = None,
        request_id: str | None = None,
    ) -> AuthorizationDecision:
        if not credential:
            raise PermissionError("missing credential")
        if not request_id:
            raise ValueError("request_id is required")

        payload = json.dumps(
            {"resource": resource, "action": action, "context": context}
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/v1/authorize",
            data=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {credential}",
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
                body = self._read_json(exc)
            except (URLError, TimeoutError, OSError) as exc:
                if attempt < self.max_retries:
                    self.sleeper(0.1 * (2**attempt))
                    continue
                raise AuthenticationServiceUnavailable(str(exc)) from exc

            if status in {500, 502, 503, 504}:
                if attempt < self.max_retries:
                    self.sleeper(0.1 * (2**attempt))
                    continue
                raise AuthenticationServiceUnavailable(
                    "authentication service is unavailable"
                )
            return self._parse_response(status, body, request_id)

        raise AuthenticationServiceUnavailable("authentication service is unavailable")

    @staticmethod
    def _read_json(response: Any) -> dict[str, Any]:
        try:
            body = json.loads(response.read().decode("utf-8"))
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuthenticationClientError("invalid authentication response") from exc
        if not isinstance(body, dict):
            raise AuthenticationClientError("authentication response must be an object")
        return body

    @staticmethod
    def _parse_response(
        status: int, body: dict[str, Any], request_id: str
    ) -> AuthorizationDecision:
        if status == 401:
            raise PermissionError(body.get("message", "authentication failed"))
        if status == 403:
            return AuthorizationDecision(False, None, request_id)
        if status != 200:
            raise AuthenticationClientError(
                body.get("message", "authentication service rejected the request")
            )

        allowed = body.get("allowed")
        response_request_id = body.get("request_id")
        if not isinstance(allowed, bool) or not isinstance(response_request_id, str):
            raise AuthenticationClientError("invalid authorization decision")
        principal = None
        if allowed:
            raw_principal = body.get("principal")
            if not isinstance(raw_principal, dict):
                raise AuthenticationClientError("allowed decision has no principal")
            scopes = raw_principal.get("scopes")
            if (
                not isinstance(raw_principal.get("subject_id"), str)
                or not isinstance(raw_principal.get("subject_type"), str)
                or not isinstance(scopes, list)
                or not all(isinstance(scope, str) for scope in scopes)
            ):
                raise AuthenticationClientError("invalid authorization principal")
            expires_at = raw_principal.get("expires_at")
            if expires_at is not None and not isinstance(expires_at, str):
                raise AuthenticationClientError("invalid principal expiry")
            principal = Principal(
                raw_principal["subject_id"],
                raw_principal["subject_type"],
                scopes,
                expires_at,
            )
        return AuthorizationDecision(allowed, principal, response_request_id)