import uuid
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from master.api import MasterApi
from master.persistence.models import Base, WorkerNode
from master.persistence.repositories import ServiceAssignmentRepository, DesiredStateRepository
from master.services import MasterNodeService, MasterReconciliationService


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
        )
        self.node_id = node_id

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


if __name__ == "__main__":
    unittest.main()