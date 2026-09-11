import json
import unittest
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from master.api import MasterApi
from master.auth import AuthenticationClient, AuthenticationServiceUnavailable
from master.persistence.models import Base, WorkerNode
from master.persistence.repositories import ServiceAssignmentRepository, DesiredStateRepository
from master.services import (
    MasterNodeService,
    MasterReconciliationService,
    MasterDomainService,
    MasterServicePlanService,
    MasterSubscriptionService,
    MasterUserService,
)


class MasterApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        node_id = str(uuid.uuid4())
        with Session(self.engine) as session, session.begin():
            session.add(WorkerNode(
                id=node_id,
                hostname="node-1",
                status="ONLINE",
                capabilities={"web": True},
                cpu_capacity=8,
                memory_capacity=8192,
                disk_capacity=100000,
                cpu_usage=0,
                memory_usage=0,
                disk_usage=0,
            ))
            ServiceAssignmentRepository(session).create_or_replace("service-123", node_id, "ASSIGNED")
            DesiredStateRepository(session).put_next("service-123", "RUNNING", {"web_server": "nginx"})

        self.api = MasterApi(
            MasterNodeService(lambda: Session(self.engine)),
            MasterReconciliationService(lambda: Session(self.engine)),
            user_service=MasterUserService(lambda: Session(self.engine)),
            service_plan_service=MasterServicePlanService(lambda: Session(self.engine)),
            subscription_service=MasterSubscriptionService(lambda: Session(self.engine)),
            domain_service=MasterDomainService(lambda: Session(self.engine)),
        )
        self.node_id = node_id

    def test_user_lifecycle_commits_and_returns_resource(self):
        created = self.api.create_user({"status": "ACTIVE"}, request_id="req-user")

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["X-Request-ID"], "req-user")
        self.assertEqual(created.body["status"], "ACTIVE")

        loaded = self.api.get_user(created.body["id"], request_id="req-user-get")

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.body, created.body)

    def test_service_plan_lifecycle_commits_and_returns_resource(self):
        created = self.api.create_service_plan(
            {
                "name": "small",
                "resource_limits": {"cpu": 2, "memory": 2048, "disk": 20000},
            },
            request_id="req-plan",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["X-Request-ID"], "req-plan")
        self.assertEqual(created.body["status"], "ACTIVE")

        loaded = self.api.get_service_plan(created.body["id"], request_id="req-plan-get")

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.body, created.body)

    def test_service_plan_requires_name(self):
        response = self.api.create_service_plan({}, request_id="req-plan-invalid")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body["code"], "INVALID_REQUEST")

    def test_subscription_lifecycle_commits_and_returns_resource(self):
        user = self.api.create_user({}, request_id="req-sub-user")
        plan = self.api.create_service_plan({"name": "subscription-plan"}, request_id="req-sub-plan")

        created = self.api.create_subscription(
            {
                "user_id": user.body["id"],
                "plan_id": plan.body["id"],
                "expires_at": "2026-12-31T00:00:00Z",
            },
            request_id="req-sub",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["X-Request-ID"], "req-sub")
        self.assertEqual(created.body["status"], "ACTIVE")
        self.assertEqual(created.body["expires_at"], "2026-12-31T00:00:00Z")

        loaded = self.api.get_subscription(created.body["id"], request_id="req-sub-get")

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.body, created.body)

    def test_subscription_requires_existing_user_and_plan(self):
        response = self.api.create_subscription(
            {"user_id": str(uuid.uuid4()), "plan_id": str(uuid.uuid4())},
            request_id="req-sub-invalid",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.body["code"], "NOT_FOUND")

    def test_domain_lifecycle_commits_and_returns_resource(self):
        user = self.api.create_user({}, request_id="req-domain-user")
        plan = self.api.create_service_plan({"name": "domain-plan"}, request_id="req-domain-plan")
        subscription = self.api.create_subscription(
            {"user_id": user.body["id"], "plan_id": plan.body["id"]},
            request_id="req-domain-subscription",
        )

        created = self.api.create_domain(
            {"subscription_id": subscription.body["id"], "name": "example.test"},
            request_id="req-domain",
        )

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["X-Request-ID"], "req-domain")
        self.assertEqual(created.body["status"], "PENDING")

        loaded = self.api.get_domain(created.body["id"], request_id="req-domain-get")

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.body, created.body)

    def test_domain_requires_existing_subscription(self):
        response = self.api.create_domain(
            {"subscription_id": str(uuid.uuid4()), "name": "example.test"},
            request_id="req-domain-invalid",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.body["code"], "NOT_FOUND")

    def test_heartbeat_returns_serialized_node_and_request_id(self):
        response = self.api.heartbeat(
            self.node_id,
            {"status": "DEGRADED", "usage": {"cpu": 2, "memory": 3500, "disk": 5000}, "last_heartbeat_at": "2026-01-01T00:10:00Z"},
            request_id="req-1",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-1")
        self.assertEqual(response.body["usage"]["memory"], 3500)

    def test_invalid_actual_state_request_is_rejected_before_service_call(self):
        response = self.api.report_actual_state("service-123", {"version": "1"}, request_id="req-2")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body["code"], "INVALID_REQUEST")
        self.assertEqual(response.body["request_id"], "req-2")

    def test_authentication_client_sends_credential_and_request_id(self):
        captured = {}

        class Response:
            def getcode(self):
                return 200

            def read(self):
                return json.dumps(
                    {
                        "allowed": True,
                        "principal": {
                            "subject_id": "user-1",
                            "subject_type": "USER",
                            "scopes": ["node:read"],
                        },
                        "request_id": "req-3",
                    }
                ).encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        def opener(request, timeout):
            captured["headers"] = request.headers
            captured["body"] = json.loads(request.data.decode())
            captured["timeout"] = timeout
            return Response()

        decision = AuthenticationClient("http://auth", opener=opener).authorize(
            "secret", "node:node-1", "read", request_id="req-3"
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.principal.subject_id, "user-1")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer secret")
        self.assertEqual(captured["headers"]["X-request-id"], "req-3")
        self.assertEqual(captured["body"]["resource"], "node:node-1")

    def test_api_passes_request_id_to_authorization_client(self):
        calls = []

        class Client:
            def authorize(self, credential, resource, action, context, request_id):
                calls.append((credential, resource, action, request_id))
                return {"allowed": True}

        api = MasterApi(
            self.api.node_service,
            self.api.reconciliation_service,
            authorization_client=Client(),
        )
        response = api.get_node(self.node_id, credential="secret", request_id="req-4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(calls, [("secret", f"node:{self.node_id}", "read", "req-4")])

    def test_api_maps_authentication_dependency_failure(self):
        class Client:
            def authorize(self, *args):
                raise AuthenticationServiceUnavailable("auth is down")

        api = MasterApi(
            self.api.node_service,
            self.api.reconciliation_service,
            authorization_client=Client(),
        )
        response = api.get_node(self.node_id, credential="secret", request_id="req-5")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.body["code"], "DEPENDENCY_UNAVAILABLE")


if __name__ == "__main__":
    unittest.main()