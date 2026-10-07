"""Production ASGI entrypoint for the isolated Web Agent service."""

from __future__ import annotations

import json
import os
import socket
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, build_opener

from .app import create_app
from .providers import NginxProvider


@dataclass(frozen=True)
class NodeRegistration:
    """Stable node identity and credential issued by Master at startup."""

    node_id: str
    credential: str
    hostname: str
    capabilities: dict[str, Any]
    capacity: dict[str, Any]


def _default_capacity() -> dict[str, Any]:
    capacity = {"cpu": 0, "memory": 0, "disk": 0}
    for name in capacity:
        raw = os.environ.get(f"WEB_AGENT_{name.upper()}_CAPACITY")
        if raw is None:
            continue
        try:
            capacity[name] = float(raw)
        except ValueError as exc:  # pragma: no cover - defensive env parsing
            raise ValueError(
                f"WEB_AGENT_{name.upper()}_CAPACITY must be numeric"
            ) from exc
    return capacity


def _resolve_capabilities() -> dict[str, Any]:
    raw = os.environ.get("WEB_AGENT_CAPABILITIES")
    if not raw:
        return {"web": True}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive env parsing
        raise ValueError("WEB_AGENT_CAPABILITIES must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise TypeError("WEB_AGENT_CAPABILITIES must be an object")
    return parsed


def register_node(
    master_service_url: str | None = None,
    bootstrap_credential: str | None = None,
    hostname: str | None = None,
    capabilities: dict[str, Any] | None = None,
    capacity: dict[str, Any] | None = None,
    opener: Callable[..., Any] | None = None,
) -> NodeRegistration:
    """Register this agent with Master and persist the returned node credential."""

    master_url = (
        master_service_url
        or os.environ.get("MASTER_SERVICE_URL", "http://localhost:8000")
    ).rstrip("/")
    node_bootstrap_credential = bootstrap_credential or os.environ.get(
        "NODE_BOOTSTRAP_CREDENTIAL", ""
    )
    if not node_bootstrap_credential:
        raise RuntimeError(
            "NODE_BOOTSTRAP_CREDENTIAL is required for startup registration"
        )

    requested_hostname = (
        hostname or os.environ.get("WEB_AGENT_HOSTNAME") or socket.gethostname()
    )
    requested_capabilities = capabilities or _resolve_capabilities()
    requested_capacity = capacity or _default_capacity()
    payload = {
        "hostname": requested_hostname,
        "capabilities": requested_capabilities,
        "capacity": requested_capacity,
        "bootstrap_credential": node_bootstrap_credential,
    }
    request = Request(
        f"{master_url}/v1/nodes/register",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        response = (opener or build_opener().open)(request, timeout=5)
        with response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except AttributeError, OSError, TypeError, ValueError:
            detail = str(exc)
        raise RuntimeError(f"Master rejected node registration: {detail}") from exc
    except (URLError, OSError, TimeoutError) as exc:
        raise RuntimeError(
            "Master node registration failed: service is unavailable"
        ) from exc
    if not isinstance(body, dict):
        raise TypeError("Master returned an invalid node-registration response")
    node_id = body.get("id")
    credential = body.get("credential")
    if (
        not isinstance(node_id, str)
        or not node_id
        or not isinstance(credential, str)
        or not credential
    ):
        raise RuntimeError(
            "Master registration response did not include a node ID and credential"
        )
    os.environ["WEB_AGENT_NODE_ID"] = node_id
    os.environ["WEB_AGENT_NODE_CREDENTIAL"] = credential
    return NodeRegistration(
        node_id=node_id,
        credential=credential,
        hostname=requested_hostname,
        capabilities=requested_capabilities,
        capacity=requested_capacity,
    )


app = create_app(
    master_token=os.environ.get("MASTER_AGENT_TOKEN", ""),
    provider=NginxProvider(),
    node_id=os.environ.get("WEB_AGENT_NODE_ID"),
    node_credential=os.environ.get("WEB_AGENT_NODE_CREDENTIAL"),
)


if __name__ == "__main__":
    register_node()
    import uvicorn

    uvicorn.run(
        "agents.web_agent.entrypoint:app",
        host=os.environ.get("WEB_AGENT_HOST", "0.0.0.0"),
        port=int(os.environ.get("WEB_AGENT_PORT", "8002")),
        log_level=os.environ.get("WEB_AGENT_LOG_LEVEL", "info"),
    )
