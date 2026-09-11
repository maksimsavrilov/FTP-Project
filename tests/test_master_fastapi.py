import asyncio
import json
import unittest
import uuid

from starlette.requests import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from master.api import MasterApi
from master.fastapi import create_app
from master.persistence.models import Base, WorkerNode
from master.services import MasterNodeService, MasterReconciliationService, MasterUserService


class FastApiAdapterTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            session.add(
                WorkerNode(
                    id=str(uuid.uuid4()),
                    hostname="node-1",
                    status="ONLINE",
                    capabilities={},
                    cpu_capacity=8,
                    memory_capacity=8192,
                    disk_capacity=100000,
                    cpu_usage=0,
                    memory_usage=0,
                    disk_usage=0,
                )
            )
        api = MasterApi(
            MasterNodeService(lambda: Session(engine)),
            MasterReconciliationService(lambda: Session(engine)),
            user_service=MasterUserService(lambda: Session(engine)),
        )
        self.app = create_app(api)

    def request(self, method, path, body=b"", request_id="req-test"):
        sent = False

        async def receive():
            nonlocal sent
            if sent:
                return {"type": "http.disconnect"}
            sent = True
            return {"type": "http.request", "body": body, "more_body": False}

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"x-request-id", request_id.encode())],
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }
        return Request(scope, receive)

    def endpoint(self, name):
        return next(route.endpoint for route in self.app.routes if route.name == name)

    def test_create_and_read_user(self):
        create = self.endpoint("create_user")
        created = asyncio.run(create(self.request("POST", "/v1/users", b"{}", "req-create")))
        created_body = json.loads(created.body)

        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.headers["X-Request-ID"], "req-create")

        read = self.endpoint("get_user")
        loaded = asyncio.run(
            read(self.request("GET", f"/v1/users/{created_body['id']}", request_id="req-read"), created_body["id"])
        )

        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(json.loads(loaded.body), created_body)

    def test_invalid_json_uses_shared_error_shape(self):
        response = asyncio.run(
            self.endpoint("create_user")(
                self.request("POST", "/v1/users", b"{", request_id="req-invalid")
            )
        )

        self.assertEqual(response.status_code, 400)
        response_body = json.loads(response.body)
        self.assertEqual(response_body["code"], "INVALID_REQUEST")
        self.assertEqual(response_body["request_id"], "req-invalid")
