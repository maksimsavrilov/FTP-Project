"""Production ASGI entrypoint for the isolated Web Agent service."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener
from uuid import uuid4

from fastapi import FastAPI

from ftp_project.worker_agent import WorkerAgentMasterClient

from .app import create_app
from .providers import NginxProvider

DEFAULT_CAPABILITIES: dict[str, Any] = {"web": True}
DEFAULT_CAPACITY: dict[str, Any] = {"cpu": 1, "memory": 1024, "disk": 10000}


def _json_config(name: str, default: dict[str, Any]) -> dict[str, Any]:
    raw_value = os.environ.get(name)
    if not raw_value:
        return default
    try:
        value = json.loads(raw_value)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{name} must be valid JSON") from exc
    if not isinstance(value, dict):
        raise TypeError(f"{name} must decode to an object")
    return value


def _post_json(url: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with build_opener().open(request, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body = {}
        message = body.get("message") if isinstance(body, dict) else str(exc)
        raise RuntimeError(
            str(message) or f"Master API request failed with status {exc.code}"
        ) from exc
    except (URLError, OSError, ValueError, UnicodeDecodeError) as exc:
        raise RuntimeError("Master service is unavailable") from exc
    if not isinstance(body, dict):
        raise TypeError("Master returned an invalid response")
    return body


def register_node(
    master_url: str | None = None,
    hostname: str | None = None,
    capabilities: dict[str, Any] | None = None,
    capacity: dict[str, Any] | None = None,
    bootstrap_credential: str | None = None,
) -> dict[str, Any]:
    master_url = (
        master_url or os.environ.get("MASTER_SERVICE_URL") or "http://master:8000"
    ).rstrip("/")
    hostname = (
        hostname
        or os.environ.get("WEB_AGENT_HOSTNAME")
        or socket.gethostname()
        or "web-agent"
    )
    capabilities = capabilities or _json_config(
        "WEB_AGENT_CAPABILITIES", DEFAULT_CAPABILITIES
    )
    capacity = capacity or _json_config("WEB_AGENT_CAPACITY", DEFAULT_CAPACITY)
    bootstrap_credential = bootstrap_credential or os.environ.get(
        "NODE_BOOTSTRAP_CREDENTIAL", ""
    )
    if not bootstrap_credential:
        raise RuntimeError(
            "NODE_BOOTSTRAP_CREDENTIAL is required to register the Web Agent"
        )

    payload = {
        "hostname": hostname,
        "capabilities": capabilities,
        "capacity": capacity,
        "bootstrap_credential": bootstrap_credential,
    }
    body = _post_json(f"{master_url}/v1/nodes/register", payload)
    if not isinstance(body.get("id"), str) or not isinstance(
        body.get("credential"), str
    ):
        raise TypeError(
            "Master node registration did not return a stable node identity"
        )
    return body


def _heartbeat_usage() -> dict[str, Any]:
    return {"cpu": 0, "memory": 0, "disk": 0}


async def _heartbeat_loop(app: FastAPI, interval_seconds: float) -> None:
    while True:
        await asyncio.sleep(interval_seconds)
        client = getattr(app.state, "node_client", None)
        node_id = getattr(app.state, "node_id", None)
        if client is None or not node_id:
            continue
        heartbeat_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            client.heartbeat(
                node_id,
                "ONLINE",
                _heartbeat_usage(),
                heartbeat_at,
                request_id=f"heartbeat-{uuid4()}",
            )
            app.state.last_heartbeat_error = None
        except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError) as exc:
            app.state.last_heartbeat_error = exc
            print(f"Web Agent heartbeat failed: {exc}", file=sys.stderr)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    registration = register_node()
    app.state.node_id = registration["id"]
    app.state.node_credential = registration["credential"]
    app.state.node_client = WorkerAgentMasterClient(
        app.state.node_credential,
        base_url=(os.environ.get("MASTER_SERVICE_URL") or "http://master:8000").rstrip("/"),
    )

    heartbeat_interval = float(os.environ.get("WEB_AGENT_HEARTBEAT_INTERVAL", "30"))
    heartbeat_task = asyncio.create_task(_heartbeat_loop(app, heartbeat_interval))
    app.state.heartbeat_task = heartbeat_task
    try:
        yield
    finally:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass


app = create_app(
    master_token=os.environ.get("MASTER_AGENT_TOKEN", ""),
    provider=NginxProvider(),
    lifespan=lifespan,
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "agents.web_agent.entrypoint:app",
        host=os.environ.get("WEB_AGENT_HOST", "0.0.0.0"),
        port=int(os.environ.get("WEB_AGENT_PORT", "8002")),
        log_level=os.environ.get("WEB_AGENT_LOG_LEVEL", "info"),
    )
