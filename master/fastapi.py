from __future__ import annotations

import json
from typing import Any, Callable
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api import ApiResponse, MasterApi


def create_app(api: MasterApi) -> FastAPI:
    """Build the HTTP adapter for the already-defined Master API boundary."""

    app = FastAPI()

    def request_context(request: Request) -> tuple[str, str | None]:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        authorization = request.headers.get("Authorization", "")
        scheme, _, credential = authorization.partition(" ")
        if scheme.lower() != "bearer" or not credential:
            return request_id, None
        return request_id, credential

    def response(result: ApiResponse) -> JSONResponse:
        return JSONResponse(
            status_code=result.status_code,
            content=result.body,
            headers=result.headers,
        )

    def invalid_request(request_id: str, message: str) -> JSONResponse:
        return response(
            ApiResponse(
                400,
                {
                    "code": "INVALID_REQUEST",
                    "message": message,
                    "request_id": request_id,
                },
                {"X-Request-ID": request_id},
            )
        )

    async def body(request: Request, request_id: str) -> dict[str, Any] | JSONResponse:
        try:
            value = json.loads((await request.body()).decode())
        except (UnicodeDecodeError, json.JSONDecodeError):
            return invalid_request(request_id, "request body must be valid JSON")
        if not isinstance(value, dict):
            return invalid_request(request_id, "request body must be an object")
        return value

    async def invoke(
        request: Request,
        operation: Callable[..., ApiResponse],
        *args: Any,
        with_body: bool = False,
        **kwargs: Any,
    ) -> JSONResponse:
        request_id, credential = request_context(request)
        if with_body:
            payload = await body(request, request_id)
            if isinstance(payload, JSONResponse):
                return payload
            args = (*args, payload)
        result = operation(*args, credential=credential, request_id=request_id, **kwargs)
        return response(result)

    @app.get("/v1/nodes")
    async def list_nodes(request: Request, status: str | None = None, capability: str | None = None):
        return await invoke(request, api.list_nodes, status=status, capability=capability)

    @app.get("/v1/nodes/{node_id}")
    async def get_node(node_id: str, request: Request):
        return await invoke(request, api.get_node, node_id)

    @app.post("/v1/nodes/{node_id}/heartbeat")
    async def heartbeat(node_id: str, request: Request):
        return await invoke(request, api.heartbeat, node_id, with_body=True)

    @app.get("/v1/services/{service_id}/state")
    async def get_state(service_id: str, request: Request):
        return await invoke(request, api.get_state, service_id)

    @app.post("/v1/services/{service_id}/actual-state")
    async def report_actual_state(service_id: str, request: Request):
        return await invoke(request, api.report_actual_state, service_id, with_body=True)

    def register_resource(path: str, name: str, method_name: str, *, create: bool = False):
        operation = getattr(api, method_name)

        async def handler(request: Request, resource_id: str | None = None):
            args = () if create else (resource_id,)
            return await invoke(request, operation, *args, with_body=create)

        if create:
            app.add_api_route(path, handler, methods=["POST"], name=name)
        else:
            app.add_api_route(f"{path}/{{resource_id}}", handler, methods=["GET"], name=name)

    resources = (
        ("users", "user", "get_user", "create_user"),
        ("service-plans", "plan", "get_service_plan", "create_service_plan"),
        ("subscriptions", "subscription", "get_subscription", "create_subscription"),
        ("domains", "domain", "get_domain", "create_domain"),
        ("websites", "website", "get_website", "create_website"),
        ("mail-domains", "mail_domain", "get_mail_domain", "create_mail_domain"),
        ("mail-accounts", "mail_account", "get_mail_account", "create_mail_account"),
        ("services", "service", "get_service", "create_service"),
        ("web-services", "web_service", "get_web_service", "create_web_service"),
        ("dns-services", "dns_service", "get_dns_service", "create_dns_service"),
        ("mail-services", "mail_service", "get_mail_service", "create_mail_service"),
        ("database-services", "database_service", "get_database_service", "create_database_service"),
        ("database-users", "database_user", "get_database_user", "create_database_user"),
    )
    for path, name, get_method, create_method in resources:
        register_resource(f"/v1/{path}", f"get_{name}", get_method)
        register_resource(f"/v1/{path}", f"create_{name}", create_method, create=True)

    register_resource("/v1/identity-references", "identity_reference", "get_identity_reference")
    register_resource("/v1/identity-references", "identity_reference", "create_identity_reference", create=True)
    register_resource("/v1/accounts", "account", "get_account")
    register_resource("/v1/accounts", "account", "create_account", create=True)

    @app.get("/v1/subscriptions/{subscription_id}/entitlements")
    async def list_entitlements(subscription_id: str, request: Request):
        return await invoke(request, api.list_entitlements, subscription_id)

    @app.get("/v1/subscriptions/{subscription_id}/entitlements/{resource_name}")
    async def get_entitlement(subscription_id: str, resource_name: str, request: Request):
        return await invoke(request, api.get_entitlement, subscription_id, resource_name)

    @app.post("/v1/subscriptions/{subscription_id}/entitlements")
    async def create_entitlement(subscription_id: str, request: Request):
        return await invoke(request, api.create_entitlement, subscription_id, with_body=True)

    return app
