from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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
    observed_configuration: dict[str, Any] = field(default_factory=dict)


class WebProvider(Protocol):
    name: str

    def validate(self, desired: Mapping[str, Any]) -> None:
        """Validate provider-neutral desired web state."""

    def generate_configuration(self, desired: Mapping[str, Any]) -> str:
        """Translate desired web state into provider configuration."""

    def apply(
        self, configuration: str | Mapping[str, Any], *, service_id: str | None = None
    ) -> ProviderApplyResult:
        """Apply generated configuration and reload the provider if needed."""

    def inspect(self, service_id: str | None = None) -> dict[str, Any]:
        """Return provider-specific actual-state diagnostics."""


class NginxProvider:
    name = "nginx"

    def __init__(
        self,
        config_path: str | Path = "/etc/nginx/conf.d/ftp-project.conf",
        nginx_config_path: str | Path | None = None,
        runtime_url: str | None = None,
        request: Callable[[str, str | None, dict[str, Any] | None], dict[str, Any]]
        | None = None,
        write_configuration: Callable[[Path, str], None] | None = None,
        run_command: Callable[[Sequence[str]], None] | None = None,
    ) -> None:
        self.config_path = Path(config_path)
        self.nginx_config_path = (
            Path(nginx_config_path)
            if nginx_config_path is not None
            else Path("/etc/nginx/nginx.conf")
        )
        self.runtime_url = runtime_url or os.environ.get("WEB_RUNTIME_URL")
        self._request = request or self._request_runtime
        self._write_configuration = write_configuration or self._write
        self._run_command = run_command or self._run

    def service_config_path(self, service_id: str) -> Path:
        if not service_id:
            return self.config_path
        return self.config_path.with_name(
            f"{self.config_path.stem}-{service_id}{self.config_path.suffix}"
        )

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

        if not self.runtime_url:
            return

        response = self._request(
            "POST",
            "/v1/services/runtime/validate",
            {"configuration": dict(desired)},
        )
        if not response.get("valid"):
            raise ProviderConfigurationError(
                response.get("message") or "runtime rejected the configuration"
            )

    def generate_configuration(self, desired: Mapping[str, Any]) -> str:
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
        self, configuration: str | Mapping[str, Any], *, service_id: str | None = None
    ) -> ProviderApplyResult:
        if self.runtime_url:
            if service_id is None:
                raise ProviderConfigurationError(
                    "service_id is required for runtime publication"
                )
            payload = (
                configuration
                if isinstance(configuration, dict)
                else {"rendered_config": configuration}
            )
            response = self._request(
                "PUT",
                f"/v1/services/{service_id}/config",
                {
                    "desired_version": "runtime",
                    "lifecycle": "STARTED",
                    "configuration": payload,
                },
            )
            if response.get("status") == "REJECTED":
                raise ProviderExecutionError(
                    response.get("details") or "runtime rejected the configuration"
                )

            observed = response.get("observed_configuration") or payload
            health = response.get("health") or {
                "provider": self.name,
                "ready": response.get("status") != "REJECTED",
            }
            return ProviderApplyResult(
                status=response.get("status", "RUNNING"),
                health={"provider": self.name, **health},
                observed_configuration=observed
                if isinstance(observed, dict)
                else {"rendered_config": observed},
            )

        target = (
            self.service_config_path(service_id) if service_id else self.config_path
        )
        try:
            self._write_configuration(
                target,
                configuration
                if isinstance(configuration, str)
                else self.generate_configuration(configuration),
            )
            self._run_command(("nginx", "-t", "-c", str(self.nginx_config_path)))
            self._run_command(("systemctl", "reload", "nginx"))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(str(exc)) from exc
        return ProviderApplyResult(
            status="RUNNING",
            health={"provider": self.name, "ready": True, "service_id": service_id},
        )

    def remove_service(self, service_id: str) -> ProviderApplyResult:
        if self.runtime_url:
            response = self._request(
                "DELETE", f"/v1/services/{service_id}/config", None
            )
            observed = response.get("observed_configuration") or {}
            return ProviderApplyResult(
                status=response.get("status", "REMOVED"),
                health={"provider": self.name, **response.get("health", {})},
                observed_configuration=observed
                if isinstance(observed, dict)
                else {"rendered_config": observed},
            )

        target = self.service_config_path(service_id)
        removed = False
        if target.exists():
            target.unlink()
            removed = True
        try:
            self._run_command(("nginx", "-t", "-c", str(self.nginx_config_path)))
            self._run_command(("systemctl", "reload", "nginx"))
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderExecutionError(str(exc)) from exc
        return ProviderApplyResult(
            status="REMOVED",
            health={
                "provider": self.name,
                "ready": True,
                "service_id": service_id,
                "removed": removed,
            },
        )

    def inspect(self, service_id: str | None = None) -> dict[str, Any]:
        if self.runtime_url:
            if service_id is None:
                return {
                    "provider": self.name,
                    "ready": False,
                    "service_id": None,
                    "observed_configuration": {},
                }
            response = self._request("GET", f"/v1/services/{service_id}/status", None)
            observed = response.get("observed_configuration") or {}
            health = response.get("health") or {
                "provider": self.name,
                "ready": response.get("status") == "RUNNING",
            }
            return {
                "provider": self.name,
                "ready": bool(health.get("ready", False)),
                "service_id": service_id,
                "status": response.get("status", "UNKNOWN"),
                "observed_configuration": observed
                if isinstance(observed, dict)
                else {"rendered_config": observed},
                "health": health,
            }

        target = (
            self.service_config_path(service_id) if service_id else self.config_path
        )
        try:
            self._run_command(("nginx", "-t", "-c", str(self.nginx_config_path)))
            ready = True
        except ProviderError:
            ready = False
        return {
            "provider": self.name,
            "ready": ready,
            "service_id": service_id,
            "config_path": str(target),
        }

    def _request_runtime(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None,
    ) -> dict[str, Any]:
        url = self.runtime_url.rstrip("/") + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=5) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            try:
                body = exc.read().decode("utf-8")
            except (UnicodeDecodeError, ValueError):
                body = "{}"
            try:
                details = json.loads(body)
            except json.JSONDecodeError:
                details = {}
            if (
                isinstance(details, dict)
                and details.get("detail", {}).get("code") == "INVALID_CONFIGURATION"
            ):
                raise ProviderConfigurationError(
                    details.get("detail", {}).get("message") or "invalid configuration"
                )
            raise ProviderExecutionError(
                details.get("message") or details.get("detail") or str(exc)
            ) from exc
        except (URLError, OSError, ValueError) as exc:
            raise ProviderExecutionError(
                f"runtime unavailable at {url}: {exc}"
            ) from exc

        try:
            loaded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise ProviderExecutionError(
                f"runtime returned invalid JSON from {url}"
            ) from exc
        if not isinstance(loaded, dict):
            raise ProviderExecutionError(
                f"runtime returned invalid response from {url}"
            )
        return loaded

    @staticmethod
    def _write(path: Path, configuration: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(configuration, encoding="utf-8")

    @staticmethod
    def _run(command: Sequence[str]) -> None:
        import subprocess

        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode:
            message = completed.stderr.strip() or "provider command failed"
            raise ProviderExecutionError(message)
