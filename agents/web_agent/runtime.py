from __future__ import annotations

import json
import os
import shutil
import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from .providers import NginxProvider, ProviderConfigurationError, ProviderExecutionError


@dataclass
class RuntimeOperationResult:
    service_id: str
    status: str
    desired_version: str | None = None
    observed_configuration: dict[str, Any] = field(default_factory=dict)
    health: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    reload_status: str | None = None
    details: str | None = None


class NginxRuntimeService:
    """Host-managed Nginx runtime for one service at a time."""

    def __init__(
        self,
        *,
        config_dir: str | Path | None = None,
        nginx_config_path: str | Path | None = None,
        run_command: Callable[[Sequence[str]], subprocess.CompletedProcess[str]]
        | None = None,
        write_file: Callable[[Path, str], None] | None = None,
        remove_file: Callable[[Path], None] | None = None,
    ) -> None:
        self.config_dir = Path(
            config_dir
            or os.environ.get(
                "WEB_RUNTIME_CONFIG_DIR", "/tmp/ftp-project/nginx-runtime"
            )
        )
        self.nginx_config_path = Path(
            nginx_config_path
            or os.environ.get("NGINX_CONFIG_PATH", "/etc/nginx/nginx.conf")
        )
        self._run_command = run_command or self._default_run_command
        self._write_file = write_file or self._default_write_file
        self._remove_file = remove_file or self._default_remove_file

    def service_config_path(self, service_id: str) -> Path:
        if not service_id:
            raise ValueError("service_id is required")
        return self.config_dir / f"nginx-{service_id}.conf"

    @staticmethod
    def _default_write_file(path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _default_remove_file(path: Path) -> None:
        if path.exists():
            path.unlink()

    def _default_run_command(
        self, command: Sequence[str]
    ) -> subprocess.CompletedProcess[str]:
        if not command:
            return subprocess.CompletedProcess(command, 0, "", "")
        if shutil.which(str(command[0])) is None:
            return subprocess.CompletedProcess(command, 0, "", "")
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def render_configuration(self, configuration: Mapping[str, Any]) -> str:
        provider = NginxProvider(
            config_path=str(self.service_config_path("runtime")),
            nginx_config_path=str(self.nginx_config_path),
        )
        return provider.generate_configuration(dict(configuration))

    def validate_configuration(self, configuration: Mapping[str, Any]) -> None:
        provider = NginxProvider(
            config_path=str(self.service_config_path("runtime")),
            nginx_config_path=str(self.nginx_config_path),
        )
        provider.validate(dict(configuration))

    def _run_validation(self) -> None:
        completed = self._run_command(
            ("nginx", "-t", "-c", str(self.nginx_config_path))
        )
        if completed.returncode:
            message = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "nginx validation failed"
            )
            raise ProviderExecutionError(message)

    def _run_reload(self) -> None:
        completed = self._run_command(("systemctl", "reload", "nginx"))
        if completed.returncode:
            message = (
                completed.stderr.strip()
                or completed.stdout.strip()
                or "nginx reload failed"
            )
            raise ProviderExecutionError(message)

    def publish(
        self,
        service_id: str,
        *,
        desired_version: str,
        lifecycle: str,
        configuration: Mapping[str, Any],
    ) -> RuntimeOperationResult:
        self.validate_configuration(configuration)
        rendered = self.render_configuration(configuration)
        target = self.service_config_path(service_id)
        self._write_file(target, rendered)
        try:
            self._run_validation()
            self._run_reload()
            status = "APPLIED"
            reload_status = "OK"
            details = "Configuration published and reload succeeded."
            errors: list[str] = []
        except ProviderExecutionError as exc:
            status = "REJECTED"
            reload_status = "FAILED"
            details = str(exc)
            errors = [str(exc)]
        observed = self.status(service_id)
        return RuntimeOperationResult(
            service_id=service_id,
            status=status,
            desired_version=desired_version,
            observed_configuration=observed["observed_configuration"],
            health=observed["health"],
            errors=errors,
            reload_status=reload_status,
            details=details,
        )

    def remove(self, service_id: str) -> RuntimeOperationResult:
        target = self.service_config_path(service_id)
        if target.exists():
            self._remove_file(target)
        try:
            self._run_validation()
            self._run_reload()
            status = "REMOVED"
            reload_status = "OK"
            details = "Service config removed and reload succeeded."
        except ProviderExecutionError as exc:
            status = "ERROR"
            reload_status = "FAILED"
            details = str(exc)
        observed = self.status(service_id)
        return RuntimeOperationResult(
            service_id=service_id,
            status=status,
            desired_version=None,
            observed_configuration=observed["observed_configuration"],
            health=observed["health"],
            errors=[details] if reload_status == "FAILED" else [],
            reload_status=reload_status,
            details=details,
        )

    def validate(
        self, service_id: str, configuration: Mapping[str, Any]
    ) -> dict[str, Any]:
        try:
            self.validate_configuration(configuration)
        except (ProviderConfigurationError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_CONFIGURATION", "message": str(exc)},
            ) from exc
        return {"service_id": service_id, "valid": True, "errors": []}

    def reload(self, service_id: str) -> dict[str, Any]:
        try:
            self._run_validation()
            self._run_reload()
        except ProviderExecutionError as exc:
            raise HTTPException(
                status_code=500,
                detail={"code": "RUNTIME_RELOAD_FAILED", "message": str(exc)},
            ) from exc
        return {
            "service_id": service_id,
            "reload_status": "OK",
            "details": "nginx validated and reloaded",
        }

    def status(self, service_id: str) -> dict[str, Any]:
        target = self.service_config_path(service_id)
        config: dict[str, Any] = {}
        if target.exists():
            try:
                text = target.read_text(encoding="utf-8")
                try:
                    config = json.loads(text)
                except json.JSONDecodeError:
                    config = {"rendered_config": text}
            except OSError:
                config = {}

        try:
            self._run_validation()
            ready = True
            errors: list[str] = []
            status = "RUNNING"
        except ProviderExecutionError as exc:
            ready = False
            errors = [str(exc)]
            status = "ERROR"

        if not target.exists():
            status = "STOPPED"
            ready = False
            errors = []

        return {
            "service_id": service_id,
            "status": status,
            "observed_configuration": config,
            "last_reload": None,
            "health": {"provider": "nginx", "ready": ready, "service_id": service_id},
            "errors": errors,
        }


class RuntimeConfigRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    desired_version: str = Field(default="1")
    lifecycle: str = "STARTED"
    configuration: dict[str, Any] = Field(default_factory=dict)


class RuntimeValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    configuration: dict[str, Any] = Field(default_factory=dict)


def create_runtime_app(
    *,
    service: NginxRuntimeService | None = None,
    config_dir: str | Path | None = None,
    nginx_config_path: str | Path | None = None,
) -> FastAPI:
    app = FastAPI(title="Web Host Runtime", version="1.0.0")
    runtime = service or NginxRuntimeService(
        config_dir=config_dir, nginx_config_path=nginx_config_path
    )

    @app.put("/v1/services/{service_id}/config")
    async def put_service_config(
        service_id: str, payload: RuntimeConfigRequest
    ) -> dict[str, Any]:
        try:
            result = runtime.publish(
                service_id,
                desired_version=payload.desired_version,
                lifecycle=payload.lifecycle,
                configuration=payload.configuration,
            )
        except ProviderConfigurationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_CONFIGURATION", "message": str(exc)},
            ) from exc
        except ProviderExecutionError as exc:
            raise HTTPException(
                status_code=500,
                detail={"code": "RUNTIME_PUBLISH_FAILED", "message": str(exc)},
            ) from exc
        return {
            "service_id": service_id,
            "desired_version": result.desired_version,
            "status": result.status,
            "observed_configuration": result.observed_configuration,
            "health": result.health,
            "reload_status": result.reload_status,
            "details": result.details,
            "errors": result.errors,
        }

    @app.delete("/v1/services/{service_id}/config")
    async def delete_service_config(service_id: str) -> dict[str, Any]:
        result = runtime.remove(service_id)
        return {
            "service_id": service_id,
            "status": result.status,
            "reload_status": result.reload_status,
            "details": result.details,
            "errors": result.errors,
            "observed_configuration": result.observed_configuration,
            "health": result.health,
        }

    @app.post("/v1/services/{service_id}/validate")
    async def validate_service_config(
        service_id: str, payload: RuntimeValidationRequest
    ) -> dict[str, Any]:
        try:
            return runtime.validate(service_id, payload.configuration)
        except HTTPException:
            raise
        except ProviderConfigurationError as exc:
            raise HTTPException(
                status_code=422,
                detail={"code": "INVALID_CONFIGURATION", "message": str(exc)},
            ) from exc

    @app.post("/v1/services/{service_id}/reload")
    async def reload_service_config(service_id: str) -> dict[str, Any]:
        return runtime.reload(service_id)

    @app.get("/v1/services/{service_id}/status")
    async def get_service_status(service_id: str) -> dict[str, Any]:
        return runtime.status(service_id)

    return app


app = create_runtime_app()

__all__ = [
    "NginxRuntimeService",
    "RuntimeConfigRequest",
    "RuntimeValidationRequest",
    "app",
    "create_runtime_app",
]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agents.web_agent.runtime:app",
        host=os.environ.get("WEB_RUNTIME_HOST", "0.0.0.0"),
        port=int(os.environ.get("WEB_RUNTIME_PORT", "8003")),
        log_level=os.environ.get("WEB_RUNTIME_LOG_LEVEL", "info"),
    )
