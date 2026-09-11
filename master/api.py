from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Protocol
from uuid import uuid4

from .auth import AuthenticationClientError, AuthenticationServiceUnavailable
from .services import MasterNodeService, MasterReconciliationService


class AuthorizationClient(Protocol):
    def authorize(
        self,
        credential: str,
        resource: str,
        action: str,
        context: object | None = None,
        request_id: str | None = None,
    ) -> Any:
        ...


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    request_id: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class ApiResponse:
    status_code: int
    body: dict[str, Any]
    headers: dict[str, str]


@dataclass(frozen=True)
class HeartbeatRequest:
    status: str
    usage: dict[str, Any]
    last_heartbeat_at: str

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> HeartbeatRequest:
        _require_object(body)
        return cls(
            status=_required_string(body, "status"),
            usage=_required_object(body, "usage"),
            last_heartbeat_at=_required_string(body, "last_heartbeat_at"),
        )


@dataclass(frozen=True)
class ActualStateRequest:
    assignment_id: str
    version: int
    status: str
    configuration: dict[str, Any]
    health: dict[str, Any]
    observed_at: str

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> ActualStateRequest:
        _require_object(body)
        version = body.get("version")
        if isinstance(version, bool) or not isinstance(version, int) or version < 0:
            raise RequestValidationError("version must be a non-negative integer")
        return cls(
            assignment_id=_required_string(body, "assignment_id"),
            version=version,
            status=_required_string(body, "status"),
            configuration=_required_object(body, "configuration"),
            health=_required_object(body, "health"),
            observed_at=_required_string(body, "observed_at"),
        )


class RequestValidationError(ValueError):
    pass


class AuthorizationDenied(PermissionError):
    pass


def _require_object(value: Any) -> None:
    if not isinstance(value, dict):
        raise RequestValidationError("request body must be an object")


def _required_string(body: dict[str, Any], name: str) -> str:
    value = body.get(name)
    if not isinstance(value, str) or not value:
        raise RequestValidationError(f"{name} must be a non-empty string")
    return value


def _required_object(body: dict[str, Any], name: str) -> dict[str, Any]:
    value = body.get(name)
    if not isinstance(value, dict):
        raise RequestValidationError(f"{name} must be an object")
    return value


def _timestamp(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        timestamp = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return _timestamp(value)
    return value


def _node_body(node: Any) -> dict[str, Any]:
    return {
        "id": str(node.id),
        "hostname": node.hostname,
        "status": node.status,
        "capabilities": node.capabilities or {},
        "capacity": {
            "cpu": _json_value(node.cpu_capacity),
            "memory": node.memory_capacity,
            "disk": node.disk_capacity,
        },
        "usage": {
            "cpu": _json_value(node.cpu_usage),
            "memory": node.memory_usage,
            "disk": node.disk_usage,
        },
        "last_heartbeat_at": _timestamp(node.last_heartbeat_at),
        "created_at": _timestamp(node.created_at),
        "updated_at": _timestamp(node.updated_at),
    }


def _state_body(state: Any) -> dict[str, Any]:
    desired = state.desired
    assignment = state.assignment
    actual = state.actual
    return {
        "desired": None
        if desired is None
        else {
            "service_id": desired.service_id,
            "version": desired.version,
            "lifecycle_state": desired.lifecycle_state,
            "configuration": desired.configuration or {},
            "updated_at": _timestamp(desired.updated_at),
        },
        "assignment": None
        if assignment is None
        else {
            "id": assignment.id,
            "service_id": assignment.service_id,
            "worker_node_id": assignment.worker_node_id,
            "status": assignment.status,
            "assigned_at": _timestamp(assignment.assigned_at),
            "released_at": _timestamp(assignment.released_at),
        },
        "actual": None
        if actual is None
        else {
            "service_id": actual.service_id,
            "assignment_id": assignment.id if assignment is not None else None,
            "version": actual.version,
            "status": actual.status,
            "configuration": actual.configuration or {},
            "health": actual.health or {},
            "observed_at": _timestamp(actual.observed_at),
        },
    }


@dataclass
class MasterApi:
    node_service: MasterNodeService
    reconciliation_service: MasterReconciliationService
    authorization_client: AuthorizationClient | None = None
    _request_id_factory: Callable[[], str] = field(default=lambda: str(uuid4()), repr=False)

    def _request_id(self, request_id: str | None) -> str:
        return request_id or self._request_id_factory()

    def _authorize(self, credential: str | None, resource: str, action: str, request_id: str) -> None:
        if self.authorization_client is None:
            return
        if not credential:
            raise PermissionError("missing credential")
        decision = self.authorization_client.authorize(
            credential, resource, action, None, request_id
        )
        allowed = decision.get("allowed", False) if isinstance(decision, dict) else getattr(decision, "allowed", False)
        if not allowed:
            raise AuthorizationDenied("request is not authorized")

    def _call(self, request_id: str, operation: Callable[[], dict[str, Any]]) -> ApiResponse:
        try:
            return ApiResponse(200, operation(), {"X-Request-ID": request_id})
        except RequestValidationError as exc:
            return self._error(400, "INVALID_REQUEST", str(exc), request_id)
        except AuthorizationDenied as exc:
            return self._error(403, "AUTHORIZATION_DENIED", str(exc), request_id)
        except PermissionError as exc:
            return self._error(401, "AUTHENTICATION_FAILED", str(exc), request_id)
        except (AuthenticationServiceUnavailable, AuthenticationClientError) as exc:
            return self._error(503, "DEPENDENCY_UNAVAILABLE", str(exc), request_id)
        except LookupError as exc:
            return self._error(404, "NOT_FOUND", str(exc), request_id)
        except ValueError as exc:
            return self._error(409, "CONFLICT", str(exc), request_id)

    @staticmethod
    def _error(status: int, code: str, message: str, request_id: str) -> ApiResponse:
        return ApiResponse(status, asdict(ApiError(code, message, request_id)), {"X-Request-ID": request_id})

    def get_node(self, node_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"node:{node_id}", "read", request_id), _node_body(self.node_service.get(node_id)))[1])

    def list_nodes(self, status: str | None = None, capability: str | None = None, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, "node:*", "read", request_id), {"items": [_node_body(node) for node in self.node_service.list(status, capability)]})[1])

    def heartbeat(self, node_id: str, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            self._authorize(credential, f"node:{node_id}", "write", request_id)
            request = HeartbeatRequest.from_dict(body)
            return _node_body(self.node_service.heartbeat(node_id, request.status, request.usage, request.last_heartbeat_at))
        return self._call(request_id, operation)

    def get_state(self, service_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"service:{service_id}", "read", request_id), _state_body(self.reconciliation_service.get_state(service_id)))[1])

    def report_actual_state(self, service_id: str, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            self._authorize(credential, f"service:{service_id}", "write", request_id)
            request = ActualStateRequest.from_dict(body)
            result = self.reconciliation_service.report_actual_state(
                service_id,
                request.assignment_id,
                request.version,
                request.status,
                request.configuration,
                request.health,
                request.observed_at,
            )
            return {"accepted": result.accepted}
        return self._call(request_id, operation)