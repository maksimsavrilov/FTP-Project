from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class AuthenticationBackendUnavailable(RuntimeError):
    """ZITADEL could not answer an introspection request."""


@dataclass(frozen=True)
class IntrospectionResult:
    subject_id: str
    subject_type: str
    scopes: list[str]
    expires_at: str | None


class ZitadelClient:
    def __init__(
        self,
        base_url: str,
        client_id: str,
        client_secret: str,
        timeout: float = 5.0,
        opener: Callable[..., Any] = urlopen,
    ):
        self.introspection_url = f"{base_url.rstrip('/')}/oauth/v2/introspect"
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self.opener = opener

    def introspect(self, credential: str) -> IntrospectionResult | None:
        if not self.client_id or not self.client_secret:
            raise AuthenticationBackendUnavailable("ZITADEL client credentials are not configured")
        basic = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode("utf-8")
        ).decode("ascii")
        request = Request(
            self.introspection_url,
            data=urlencode({"token": credential}).encode("ascii"),
            headers={
                "Accept": "application/json",
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {basic}",
            },
            method="POST",
        )
        try:
            with self.opener(request, timeout=self.timeout) as response:
                status = response.getcode()
                body = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AuthenticationBackendUnavailable("ZITADEL introspection failed") from exc
        if status >= 500:
            raise AuthenticationBackendUnavailable("ZITADEL introspection failed")
        if status != 200 or not isinstance(body, dict):
            return None
        if body.get("active") is not True or not isinstance(body.get("sub"), str):
            return None
        scopes = body.get("scope", "")
        if isinstance(scopes, str):
            scope_list = [scope for scope in scopes.split() if scope]
        elif isinstance(scopes, list) and all(isinstance(scope, str) for scope in scopes):
            scope_list = scopes
        else:
            scope_list = []
        return IntrospectionResult(
            subject_id=body["sub"],
            subject_type="SERVICE" if body.get("client_id") else "USER",
            scopes=scope_list,
            expires_at=body.get("exp") if isinstance(body.get("exp"), str) else None,
        )


def create_client() -> ZitadelClient:
    return ZitadelClient(
        os.environ.get("ZITADEL_URL", "http://zitadel:8080"),
        os.environ.get("ZITADEL_CLIENT_ID", ""),
        os.environ.get("ZITADEL_CLIENT_SECRET", ""),
    )


def authorize(
    client: ZitadelClient,
    credential: str | None,
    resource: Any,
    action: Any,
    context: Any,
    request_id: str,
) -> tuple[int, dict[str, Any]]:
    if not credential:
        return 401, _error("AUTHENTICATION_FAILED", "authentication required", request_id)
    if not isinstance(resource, str) or not resource or not isinstance(action, str) or not action:
        return 400, _error("INVALID_REQUEST", "resource and action are required", request_id)
    if context is not None and not isinstance(context, dict):
        return 400, _error("INVALID_REQUEST", "context must be an object", request_id)

    principal = client.introspect(credential)
    if principal is None:
        return 401, _error("AUTHENTICATION_FAILED", "authentication failed", request_id)
    resource_type = resource.split(":", 1)[0]
    required_scope = f"{resource_type}:{action}"
    allowed = required_scope in principal.scopes or f"*:{action}" in principal.scopes or "*" in principal.scopes
    if not allowed:
        return 200, {"allowed": False, "request_id": request_id}
    return 200, {
        "allowed": True,
        "principal": {
            "subject_id": principal.subject_id,
            "subject_type": principal.subject_type,
            "scopes": principal.scopes,
            **({"expires_at": principal.expires_at} if principal.expires_at else {}),
        },
        "request_id": request_id,
    }


def _error(code: str, message: str, request_id: str) -> dict[str, str]:
    return {"code": code, "message": message, "request_id": request_id}
