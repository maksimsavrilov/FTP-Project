from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Callable, Protocol
from uuid import uuid4

from ..auth import AuthenticationClientError, AuthenticationServiceUnavailable
from ..services import (
    MasterDatabaseServiceService,
    MasterDatabaseUserService,
    MasterNodeService,
    MasterReconciliationService,
    MasterDomainService,
    MasterDnsServiceService,
    MasterMailAccountService,
    MasterMailDomainService,
    MasterMailServiceService,
    MasterAccountService,
    MasterIdentityReferenceService,
    MasterResourceEntitlementService,
    MasterServiceService,
    MasterServicePlanService,
    MasterSubscriptionService,
    MasterUserService,
    MasterWebsiteService,
    MasterWebServiceService,
)


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
class NodeRegistrationRequest:
    hostname: str
    capabilities: dict[str, Any]
    capacity: dict[str, Any]
    bootstrap_credential: str

    @classmethod
    def from_dict(cls, body: dict[str, Any]) -> NodeRegistrationRequest:
        _require_object(body)
        capacity = _required_object(body, "capacity")
        for name in ("cpu", "memory", "disk"):
            value = capacity.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
                raise RequestValidationError(f"capacity.{name} must be non-negative")
        return cls(
            hostname=_required_string(body, "hostname"),
            capabilities=_required_object(body, "capabilities"),
            capacity=capacity,
            bootstrap_credential=_required_string(body, "bootstrap_credential"),
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


def _registration_body(result: Any) -> dict[str, Any]:
    body = _node_body(result.node)
    body["credential"] = result.credential
    return body


def _user_body(user: Any) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "status": user.status,
        "created_at": _timestamp(user.created_at),
        "updated_at": _timestamp(user.updated_at),
    }


def _service_plan_body(plan: Any) -> dict[str, Any]:
    return {
        "id": str(plan.id),
        "name": plan.name,
        "status": plan.status,
        "resource_limits": plan.resource_limits or {},
        "object_limits": plan.object_limits or {},
        "created_at": _timestamp(plan.created_at),
        "updated_at": _timestamp(plan.updated_at),
    }


def _subscription_body(subscription: Any) -> dict[str, Any]:
    return {
        "id": str(subscription.id),
        "user_id": str(subscription.user_id),
        "plan_id": str(subscription.plan_id),
        "status": subscription.status,
        "created_at": _timestamp(subscription.created_at),
        "expires_at": _timestamp(subscription.expires_at),
    }


def _identity_reference_body(identity: Any) -> dict[str, Any]:
    return {"id": str(identity.id), "provider": identity.provider, "subject_id": identity.subject_id}


def _account_body(account: Any) -> dict[str, Any]:
    return {
        "id": str(account.id),
        "role": account.role,
        "status": account.status,
        "identity_reference_id": account.identity_reference_id,
        "parent_account_id": account.parent_account_id,
        "created_at": _timestamp(account.created_at),
        "updated_at": _timestamp(account.updated_at),
    }


def _entitlement_body(entitlement: Any) -> dict[str, Any]:
    return {
        "id": str(entitlement.id),
        "subscription_id": str(entitlement.subscription_id),
        "resource_name": entitlement.resource_name,
        "limit": _json_value(entitlement.limit),
        "usage": _json_value(entitlement.usage),
        "reservation": _json_value(entitlement.reservation),
        "source": entitlement.source,
    }


def _domain_body(domain: Any) -> dict[str, Any]:
    return {
        "id": str(domain.id),
        "subscription_id": str(domain.subscription_id),
        "name": domain.name,
        "status": domain.status,
        "created_at": _timestamp(domain.created_at),
    }


def _website_body(website: Any) -> dict[str, Any]:
    return {
        "id": str(website.id),
        "domain_id": str(website.domain_id),
        "status": website.status,
        "document_root": website.document_root,
        "created_at": _timestamp(website.created_at),
    }


def _mail_domain_body(mail_domain: Any) -> dict[str, Any]:
    return {
        "id": str(mail_domain.id),
        "domain_id": str(mail_domain.domain_id),
        "status": mail_domain.status,
        "created_at": _timestamp(mail_domain.created_at),
    }


def _mail_account_body(mail_account: Any) -> dict[str, Any]:
    return {
        "id": str(mail_account.id),
        "mail_domain_id": str(mail_account.mail_domain_id),
        "address": mail_account.address,
        "status": mail_account.status,
        "created_at": _timestamp(mail_account.created_at),
    }


def _service_body(result: Any) -> dict[str, Any]:
    return {
        "id": str(result.id),
        "subscription_id": str(result.subscription_id),
        "type": result.type,
        "status": result.status,
        "created_at": _timestamp(result.created_at),
        "updated_at": _timestamp(result.updated_at),
        "assignment": {
            "id": str(result.assignment_id),
            "worker_node_id": str(result.worker_node_id),
            "status": result.assignment_status,
        },
        "desired_state": {
            "version": result.desired_version,
            "lifecycle_state": result.lifecycle_state,
            "configuration": result.configuration,
            "updated_at": _timestamp(result.desired_updated_at),
        },
    }


def _web_service_body(result: Any) -> dict[str, Any]:
    body = _service_body(result.service)
    body.update(
        {
            "website_id": str(result.website_id),
            "web_server": result.web_server,
            "php_version": result.php_version,
            "document_root": result.document_root,
        }
    )
    return body


def _dns_service_body(result: Any) -> dict[str, Any]:
    return _service_body(result.service)


def _mail_service_body(result: Any) -> dict[str, Any]:
    return _service_body(result.service)


def _database_service_body(result: Any) -> dict[str, Any]:
    body = _service_body(result.service)
    body.update(
        {
            "database_type": result.database_type,
            "database_name": result.database_name,
        }
    )
    return body


def _database_user_body(database_user: Any) -> dict[str, Any]:
    return {
        "id": str(database_user.id),
        "database_service_id": str(database_user.database_service_id),
        "username": database_user.username,
        "status": database_user.status,
        "privileges": database_user.privileges or {},
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
    user_service: MasterUserService | None = None
    service_plan_service: MasterServicePlanService | None = None
    subscription_service: MasterSubscriptionService | None = None
    domain_service: MasterDomainService | None = None
    website_service: MasterWebsiteService | None = None
    service_service: MasterServiceService | None = None
    web_service_service: MasterWebServiceService | None = None
    dns_service_service: MasterDnsServiceService | None = None
    mail_service_service: MasterMailServiceService | None = None
    database_service_service: MasterDatabaseServiceService | None = None
    database_user_service: MasterDatabaseUserService | None = None
    mail_domain_service: MasterMailDomainService | None = None
    mail_account_service: MasterMailAccountService | None = None
    identity_reference_service: MasterIdentityReferenceService | None = None
    account_service: MasterAccountService | None = None
    resource_entitlement_service: MasterResourceEntitlementService | None = None
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
        allowed = decision.get("allowed") if isinstance(decision, dict) else getattr(decision, "allowed", None)
        if not isinstance(allowed, bool):
            raise AuthenticationClientError("invalid authorization decision")
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
        def operation() -> dict[str, Any]:
            node = self.node_service.get(node_id)
            if node is None:
                raise LookupError(f"WorkerNode {node_id} not found")
            if node.credential_hash is not None:
                if not self.node_service.authenticate(node_id, credential):
                    raise PermissionError("invalid node credential")
            else:
                self._authorize(credential, f"node:{node_id}", "read", request_id)
            return _node_body(node)
        return self._call(request_id, operation)

    def register_node(self, body: dict[str, Any], request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            request = NodeRegistrationRequest.from_dict(body)
            result = self.node_service.register(
                request.hostname,
                request.capabilities,
                request.capacity,
                request.bootstrap_credential,
            )
            return _registration_body(result)
        response = self._call(request_id, operation)
        return ApiResponse(201, response.body, response.headers) if response.status_code == 200 else response

    def list_nodes(self, status: str | None = None, capability: str | None = None, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, "node:*", "read", request_id), {"items": [_node_body(node) for node in self.node_service.list(status, capability)]})[1])

    def heartbeat(self, node_id: str, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            request = HeartbeatRequest.from_dict(body)
            node = self.node_service.get(node_id)
            if node is None:
                raise LookupError(f"WorkerNode {node_id} not found")
            if node.credential_hash is not None:
                if not self.node_service.authenticate(node_id, credential):
                    raise PermissionError("invalid node credential")
            else:
                self._authorize(credential, f"node:{node_id}", "write", request_id)
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

    def get_user(self, user_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"user:{user_id}", "read", request_id), _user_body(self.user_service.get(user_id)))[1])

    def create_user(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "user:*", "write", request_id)
            _require_object(body)
            status = body.get("status", "ACTIVE")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            return _user_body(self.user_service.create(status))

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_service_plan(self, plan_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"service-plan:{plan_id}", "read", request_id), _service_plan_body(self.service_plan_service.get(plan_id)))[1])

    def create_service_plan(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "service-plan:*", "write", request_id)
            _require_object(body)
            name = _required_string(body, "name")
            status = body.get("status", "ACTIVE")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            resource_limits = body.get("resource_limits", {})
            if not isinstance(resource_limits, dict):
                raise RequestValidationError("resource_limits must be an object")
            object_limits = body.get("object_limits", {})
            if not isinstance(object_limits, dict):
                raise RequestValidationError("object_limits must be an object")
            return _service_plan_body(
                self.service_plan_service.create(
                    name, status, resource_limits, object_limits
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_subscription(self, subscription_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"subscription:{subscription_id}", "read", request_id), _subscription_body(self.subscription_service.get(subscription_id)))[1])

    def create_subscription(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "subscription:*", "write", request_id)
            _require_object(body)
            user_id = _required_string(body, "user_id")
            plan_id = _required_string(body, "plan_id")
            status = body.get("status", "ACTIVE")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            expires_at = body.get("expires_at")
            if expires_at is not None and (not isinstance(expires_at, str) or not expires_at):
                raise RequestValidationError("expires_at must be a non-empty string or null")
            return _subscription_body(
                self.subscription_service.create(user_id, plan_id, status, expires_at)
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_identity_reference(self, identity_reference_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"identity-reference:{identity_reference_id}", "read", request_id), _identity_reference_body(self.identity_reference_service.get(identity_reference_id)))[1])

    def create_identity_reference(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            self._authorize(credential, "identity-reference:*", "write", request_id)
            _require_object(body)
            return _identity_reference_body(self.identity_reference_service.create(_required_string(body, "provider"), _required_string(body, "subject_id")))
        response = self._call(request_id, operation)
        return ApiResponse(201, response.body, response.headers) if response.status_code == 200 else response

    def get_account(self, account_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"account:{account_id}", "read", request_id), _account_body(self.account_service.get(account_id)))[1])

    def create_account(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            self._authorize(credential, "account:*", "write", request_id)
            _require_object(body)
            role = _required_string(body, "role")
            status = body.get("status", "ACTIVE")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            identity_reference_id = body.get("identity_reference_id")
            parent_account_id = body.get("parent_account_id")
            for name, value in (("identity_reference_id", identity_reference_id), ("parent_account_id", parent_account_id)):
                if value is not None and (not isinstance(value, str) or not value):
                    raise RequestValidationError(f"{name} must be a non-empty string or null")
            return _account_body(self.account_service.create(role, status, identity_reference_id, parent_account_id))
        response = self._call(request_id, operation)
        return ApiResponse(201, response.body, response.headers) if response.status_code == 200 else response

    def list_entitlements(self, subscription_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"subscription:{subscription_id}", "read", request_id), {"items": [_entitlement_body(item) for item in self.resource_entitlement_service.list(subscription_id)]})[1])

    def get_entitlement(self, subscription_id: str, resource_name: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"subscription:{subscription_id}", "read", request_id), _entitlement_body(self.resource_entitlement_service.get(subscription_id, resource_name)))[1])

    def create_entitlement(self, subscription_id: str, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        def operation() -> dict[str, Any]:
            self._authorize(credential, f"subscription:{subscription_id}", "write", request_id)
            _require_object(body)
            resource_name = _required_string(body, "resource_name")
            source = _required_string(body, "source")
            values = {name: body.get(name, 0) for name in ("limit", "usage", "reservation")}
            for name, value in values.items():
                if isinstance(value, bool) or not isinstance(value, (int, float, str)):
                    raise RequestValidationError(f"{name} must be numeric")
            return _entitlement_body(self.resource_entitlement_service.create(subscription_id, resource_name, values["limit"], source, values["usage"], values["reservation"]))
        response = self._call(request_id, operation)
        return ApiResponse(201, response.body, response.headers) if response.status_code == 200 else response

    def get_domain(self, domain_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"domain:{domain_id}", "read", request_id), _domain_body(self.domain_service.get(domain_id)))[1])

    def create_domain(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "domain:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            name = _required_string(body, "name")
            status = body.get("status", "PENDING")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            return _domain_body(self.domain_service.create(subscription_id, name, status))

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_website(self, website_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"website:{website_id}", "read", request_id), _website_body(self.website_service.get(website_id)))[1])

    def create_website(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "website:*", "write", request_id)
            _require_object(body)
            domain_id = _required_string(body, "domain_id")
            document_root = _required_string(body, "document_root")
            status = body.get("status", "PENDING")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            return _website_body(self.website_service.create(domain_id, document_root, status))

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_mail_domain(self, mail_domain_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"mail-domain:{mail_domain_id}", "read", request_id), _mail_domain_body(self.mail_domain_service.get(mail_domain_id)))[1])

    def create_mail_domain(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "mail-domain:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            domain_id = _required_string(body, "domain_id")
            status = body.get("status", "PENDING")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            return _mail_domain_body(
                self.mail_domain_service.create(subscription_id, domain_id, status)
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_mail_account(self, mail_account_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"mail-account:{mail_account_id}", "read", request_id), _mail_account_body(self.mail_account_service.get(mail_account_id)))[1])

    def create_mail_account(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "mail-account:*", "write", request_id)
            _require_object(body)
            mail_domain_id = _required_string(body, "mail_domain_id")
            address = _required_string(body, "address")
            status = body.get("status", "PENDING")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            return _mail_account_body(
                self.mail_account_service.create(mail_domain_id, address, status)
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_service(self, service_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"service:{service_id}", "read", request_id), _service_body(self.service_service.get(service_id)))[1])

    def create_service(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "service:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            service_type = _required_string(body, "type")
            allocation = _required_object(body, "allocation")
            lifecycle_state = _required_string(body, "lifecycle_state")
            configuration = _required_object(body, "configuration")
            return _service_body(
                self.service_service.create(
                    subscription_id,
                    service_type,
                    allocation,
                    lifecycle_state,
                    configuration,
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_web_service(self, service_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"web-service:{service_id}", "read", request_id), _web_service_body(self.web_service_service.get(service_id)))[1])

    def create_web_service(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "web-service:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            website_id = _required_string(body, "website_id")
            allocation = _required_object(body, "allocation")
            lifecycle_state = _required_string(body, "lifecycle_state")
            web_server = _required_string(body, "web_server")
            php_version = _required_string(body, "php_version")
            document_root = _required_string(body, "document_root")
            return _web_service_body(
                self.web_service_service.create(
                    subscription_id,
                    website_id,
                    allocation,
                    lifecycle_state,
                    web_server,
                    php_version,
                    document_root,
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_dns_service(self, service_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"dns-service:{service_id}", "read", request_id), _dns_service_body(self.dns_service_service.get(service_id)))[1])

    def create_dns_service(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "dns-service:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            domain_id = _required_string(body, "domain_id")
            allocation = _required_object(body, "allocation")
            lifecycle_state = _required_string(body, "lifecycle_state")
            configuration = _required_object(body, "configuration")
            return _dns_service_body(
                self.dns_service_service.create(
                    subscription_id,
                    domain_id,
                    allocation,
                    lifecycle_state,
                    configuration,
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_mail_service(self, service_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"mail-service:{service_id}", "read", request_id), _mail_service_body(self.mail_service_service.get(service_id)))[1])

    def create_mail_service(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "mail-service:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            domain_id = _required_string(body, "domain_id")
            allocation = _required_object(body, "allocation")
            lifecycle_state = _required_string(body, "lifecycle_state")
            configuration = _required_object(body, "configuration")
            return _mail_service_body(
                self.mail_service_service.create(
                    subscription_id,
                    domain_id,
                    allocation,
                    lifecycle_state,
                    configuration,
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_database_service(self, service_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"database-service:{service_id}", "read", request_id), _database_service_body(self.database_service_service.get(service_id)))[1])

    def create_database_service(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "database-service:*", "write", request_id)
            _require_object(body)
            subscription_id = _required_string(body, "subscription_id")
            allocation = _required_object(body, "allocation")
            lifecycle_state = _required_string(body, "lifecycle_state")
            database_type = _required_string(body, "database_type")
            database_name = _required_string(body, "database_name")
            return _database_service_body(
                self.database_service_service.create(
                    subscription_id,
                    allocation,
                    lifecycle_state,
                    database_type,
                    database_name,
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response

    def get_database_user(self, database_user_id: str, credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)
        return self._call(request_id, lambda: (self._authorize(credential, f"database-user:{database_user_id}", "read", request_id), _database_user_body(self.database_user_service.get(database_user_id)))[1])

    def create_database_user(self, body: dict[str, Any], credential: str | None = None, request_id: str | None = None) -> ApiResponse:
        request_id = self._request_id(request_id)

        def operation() -> dict[str, Any]:
            self._authorize(credential, "database-user:*", "write", request_id)
            _require_object(body)
            database_service_id = _required_string(body, "database_service_id")
            username = _required_string(body, "username")
            status = body.get("status", "PENDING")
            if not isinstance(status, str) or not status:
                raise RequestValidationError("status must be a non-empty string")
            privileges = body.get("privileges", {})
            if not isinstance(privileges, dict):
                raise RequestValidationError("privileges must be an object")
            return _database_user_body(
                self.database_user_service.create(
                    database_service_id, username, status, privileges
                )
            )

        response = self._call(request_id, operation)
        if response.status_code == 200:
            return ApiResponse(201, response.body, response.headers)
        return response
