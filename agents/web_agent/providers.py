from __future__ import annotations

import http.client
import json
import socket
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


class ProviderError(Exception):
    """Base error for provider validation and execution failures."""


class ProviderConfigurationError(ProviderError):
    """The desired state cannot be represented by the provider."""


class ProviderExecutionError(ProviderError):
    """The provider could not apply or inspect its local state."""


@dataclass(frozen=True)
class ProviderApplyResult:
    status: str
    health: dict[str, Any] = field(default_factory=dict)


class WebProvider(Protocol):
    name: str

    def validate(self, desired: Mapping[str, Any]) -> None: ...

    def generate_configuration(self, desired: Mapping[str, Any]) -> str: ...

    def apply(
        self, configuration: str, *, service_id: str, version: int
    ) -> ProviderApplyResult: ...

    def inspect(self, service_id: str) -> dict[str, Any]: ...


class UnixSocketHTTPConnection(http.client.HTTPConnection):
    def __init__(self, socket_path: str, timeout: float = 5) -> None:
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(self.timeout)
        connection.connect(self.socket_path)
        self.sock = connection


class NginxProvider:
    name = "nginx"

    def __init__(self, socket_path: str = "/run/web-service/adapter.sock") -> None:
        self.socket_path = socket_path

    def validate(self, desired: Mapping[str, Any]) -> None:
        required = ("hostname", "document_root")
        missing = [field for field in required if not desired.get(field)]
        if missing:
            raise ProviderConfigurationError(
                f"missing required web configuration: {', '.join(missing)}"
            )
        if not str(desired["hostname"]).strip():
            raise ProviderConfigurationError("hostname must not be empty")
        if not str(desired["document_root"]).startswith("/"):
            raise ProviderConfigurationError("document_root must be an absolute path")

    def generate_configuration(self, desired: Mapping[str, Any]) -> str:
        self.validate(desired)
        hostname = str(desired["hostname"])
        document_root = str(desired["document_root"])
        lines = [
            "server {",
            "    listen 80;",
            f"    server_name {hostname};",
            f"    root {document_root};",
            "    index index.php index.html;",
        ]
        php_version = desired.get("php_version")
        if php_version:
            lines.append(f"    # PHP runtime: {php_version}")
        if desired.get("tls"):
            lines.append("    # TLS is enabled by the provider deployment policy.")
        lines.extend(["}", ""])
        return "\n".join(lines)

    def apply(
        self, configuration: str, *, service_id: str, version: int = 1
    ) -> ProviderApplyResult:
        state = self._request(
            "/v1/apply",
            {
                "service_id": service_id,
                "version": version,
                "configuration": configuration,
            },
        )
        return ProviderApplyResult(
            status=str(state.get("status", "ERROR")),
            health={"provider": self.name, "ready": state.get("ready", False)},
        )

    def remove_service(self, service_id: str) -> ProviderApplyResult:
        state = self._request("/v1/remove", {"service_id": service_id})
        return ProviderApplyResult(
            status="REMOVED",
            health={
                "provider": self.name,
                "ready": state.get("ready", False),
                "service_id": service_id,
                "removed": state.get("removed", False),
            },
        )

    def inspect(self, service_id: str) -> dict[str, Any]:
        state = self._request("/v1/observe", {"service_id": service_id})
        return {"provider": self.name, **state}

    def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        connection = UnixSocketHTTPConnection(self.socket_path)
        try:
            connection.request(
                "POST",
                path,
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response = connection.getresponse()
            body = json.loads(response.read())
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as exc:
            raise ProviderExecutionError(
                f"Web service adapter unavailable: {exc}"
            ) from exc
        finally:
            connection.close()

        if not isinstance(body, dict):
            raise ProviderExecutionError(
                "Web service adapter returned an invalid response"
            )
        if response.status >= 400:
            error = body.get("error")
            message = error.get("message") if isinstance(error, dict) else None
            code = error.get("code") if isinstance(error, dict) else None
            exception = (
                ProviderConfigurationError
                if response.status < 500
                else ProviderExecutionError
            )
            raise exception(f"{code or 'ADAPTER_ERROR'}: {message or response.status}")
        state = body.get("state")
        if not isinstance(state, dict):
            raise ProviderExecutionError(
                "Web service adapter response omitted observed state"
            )
        return state
