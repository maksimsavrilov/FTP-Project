from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast


class AdapterError(Exception):
    def __init__(self, code: str, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.status = status


class NginxRuntime:
    def __init__(
        self,
        config_dir: str | Path = "/etc/nginx/conf.d/services",
        nginx_config: str | Path = "/etc/nginx/nginx.conf",
        nginx_pid: str | Path = "/var/run/nginx.pid",
        run_command: Any = None,
    ) -> None:
        self.config_dir = Path(config_dir)
        self.nginx_config = Path(nginx_config)
        self.nginx_pid = Path(nginx_pid)
        self.run_command = run_command or self._run_command
        self._lock = threading.RLock()

    def apply(
        self, service_id: str, version: int, configuration: str
    ) -> dict[str, Any]:
        target = self._service_path(service_id)
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            raise AdapterError("INVALID_VERSION", "version must be a positive integer")
        if not configuration.strip():
            raise AdapterError(
                "INVALID_CONFIGURATION", "configuration must not be empty"
            )
        with self._lock:
            previous = target.read_bytes() if target.exists() else None
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_suffix(".conf.tmp")
                temporary.write_text(configuration, encoding="utf-8")
                temporary.replace(target)
                self.run_command(("nginx", "-t", "-c", str(self.nginx_config)))
                self.run_command(
                    ("nginx", "-s", "reload", "-c", str(self.nginx_config))
                )
            except Exception as exc:
                if previous is None:
                    target.unlink(missing_ok=True)
                else:
                    target.write_bytes(previous)
                raise AdapterError("NGINX_APPLY_FAILED", str(exc), 500) from exc
        return self.observe(service_id)

    def remove(self, service_id: str) -> dict[str, Any]:
        target = self._service_path(service_id)
        with self._lock:
            previous = target.read_bytes() if target.exists() else None
            try:
                removed = target.exists()
                target.unlink(missing_ok=True)
                self.run_command(("nginx", "-t", "-c", str(self.nginx_config)))
                self.run_command(
                    ("nginx", "-s", "reload", "-c", str(self.nginx_config))
                )
            except Exception as exc:
                if previous is not None:
                    target.write_bytes(previous)
                raise AdapterError("NGINX_REMOVE_FAILED", str(exc), 500) from exc
        state = self.observe(service_id)
        state["removed"] = removed
        return state

    def observe(self, service_id: str) -> dict[str, Any]:
        target = self._service_path(service_id)
        with self._lock:
            try:
                self.run_command(("nginx", "-t", "-c", str(self.nginx_config)))
                configuration = (
                    target.read_text(encoding="utf-8") if target.exists() else None
                )
            except Exception as exc:
                raise AdapterError("NGINX_OBSERVE_FAILED", str(exc), 500) from exc
            running = self._nginx_running()
        return {
            "service_id": service_id,
            "status": (
                "RUNNING"
                if configuration is not None and running
                else "STOPPED"
                if configuration is not None
                else "ABSENT"
            ),
            "ready": running,
            "configuration": configuration,
        }

    def _nginx_running(self) -> bool:
        try:
            pid = int(self.nginx_pid.read_text(encoding="utf-8").strip())
        except OSError, ValueError:
            return False
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True

    def _service_path(self, service_id: str) -> Path:
        if not isinstance(service_id, str) or not re.fullmatch(
            r"[A-Za-z0-9_-]{1,128}", service_id
        ):
            raise AdapterError(
                "INVALID_SERVICE_ID",
                "service_id must contain only letters, digits, '_' or '-'",
            )
        return self.config_dir / f"service-{service_id}.conf"

    @staticmethod
    def _run_command(command: tuple[str, ...]) -> None:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "nginx command failed")


class UnixThreadingHTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_UNIX
    allow_reuse_address = False

    def __init__(
        self,
        server_address: str,
        request_handler: type[BaseHTTPRequestHandler],
    ) -> None:
        super().__init__(cast(Any, server_address), request_handler)


def create_server(
    runtime: NginxRuntime, socket_path: str | Path
) -> UnixThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/health":
                self._respond(
                    404, {"error": {"code": "NOT_FOUND", "message": "route not found"}}
                )
                return
            try:
                state = runtime.observe("healthcheck")
                self._respond(200 if state["ready"] else 503, {"ready": state["ready"]})
            except AdapterError as exc:
                self._respond(
                    exc.status, {"error": {"code": exc.code, "message": str(exc)}}
                )

        def do_POST(self) -> None:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length > 1_048_576:
                    raise AdapterError(
                        "REQUEST_TOO_LARGE", "request body exceeds 1 MiB", 413
                    )
                payload: object = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise AdapterError(
                        "INVALID_REQUEST", "request body must be a JSON object"
                    )
                request = cast(dict[str, object], payload)
                action = self.path
                service_id = request.get("service_id")
                if not isinstance(service_id, str):
                    raise AdapterError("INVALID_REQUEST", "service_id must be a string")
                if action == "/v1/apply":
                    version = request.get("version")
                    configuration = request.get("configuration")
                    if isinstance(version, bool) or not isinstance(version, int):
                        raise AdapterError(
                            "INVALID_REQUEST", "version must be an integer"
                        )
                    if not isinstance(configuration, str):
                        raise AdapterError(
                            "INVALID_REQUEST", "configuration must be a string"
                        )
                    state = runtime.apply(
                        service_id,
                        version,
                        configuration,
                    )
                elif action == "/v1/remove":
                    state = runtime.remove(service_id)
                elif action == "/v1/observe":
                    state = runtime.observe(service_id)
                else:
                    raise AdapterError("NOT_FOUND", "operation not found", 404)
                self._respond(200, {"state": state})
            except AdapterError as exc:
                self._respond(
                    exc.status, {"error": {"code": exc.code, "message": str(exc)}}
                )
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._respond(
                    400, {"error": {"code": "INVALID_REQUEST", "message": str(exc)}}
                )

        def _respond(self, status: int, value: dict[str, Any]) -> None:
            body = json.dumps(value).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            return

    path = Path(socket_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    server = UnixThreadingHTTPServer(str(path), Handler)
    os.chmod(path, 0o660)
    return server


def main() -> None:
    server = create_server(
        NginxRuntime(),
        os.environ.get("WEB_SERVICE_SOCKET", "/run/web-service/adapter.sock"),
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
